# -*- coding: utf-8 -*-
"""
AI 面试官 - FastAPI 后端
支持真正的流式 TTS：LLM 生成一句就立即 TTS 并播放
"""
import asyncio
import base64
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 确保项目根目录在 sys.path 中
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    STEPFUN_API_KEY,
    TEMP_DIR,
    init_directories,
)
from modules.llm_agent import llm_stream_chat
from modules.rag_engine import get_retrieved_context
from modules.audio_processor import (
    EdgeTTS_async,
    transcribe_file,
    _strip_markdown,
)
from modules.ai_report import ai_report_stream, _format_history_for_report
from modules.resume_parser import parse_resume, format_resume_for_prompt
from modules.advisor_search import search_advisor_info, search_advisor_stream, format_advisor_info_for_prompt

# 初始化目录
init_directories()

# ==================== FastAPI 应用 ====================
app = FastAPI(title="AI 面试官", version="2.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ==================== 数据模型 ====================
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    system_prompt: str = ""
    enable_tts: bool = True
    enable_rag: bool = True
    rag_domain: str = "cs"
    rag_top_k: int = 6


class SettingsModel(BaseModel):
    prompt_choice: str = "正常型面试官（默认）"
    system_prompt: str = ""
    enable_tts: bool = True
    enable_rag: bool = True
    rag_domain: str = "cs"
    rag_top_k: int = 6
    compact_mode: bool = False  # 精简对话模式


class CodeExecuteRequest(BaseModel):
    """代码执行请求模型"""
    code: str
    language: str  # python, javascript, java, cpp
    stdin: str = ""


# ==================== 全局状态 ====================
# 使用内存存储会话状态（生产环境应使用 Redis 等）
session_store: Dict[str, Any] = {
    "history": [],
    "rag_history": [],
    "settings": SettingsModel().model_dump(),
    "resume_uploaded": False,
    "resume_analysis": None,
    "resume_file_name": "",
    "advisor_searched": False,
    "advisor_info": None,
    "advisor_school": "",
    "advisor_name": "",
}

# 预设系统提示词 - 基础流程
default_prompt = """
你是一位技术面试官。请严格按照以下 7 个环节完成一轮面试，并在每一步只做当前环节的事。

【总体要求】
1) 全程问答式推进，一次只提一个核心问题。
2) 每次回复简洁、清晰、可执行，不要使用表情符号。
3) 重点考察：理解能力、技术深度、分析能力、实现细节、边界条件、工程可行性。
4) 候选人回答不清晰时，先追问澄清，不要提前进入下一环节。

【7 个环节与编号（一一对应）】
- 0 = 面试开始
- 1 = 自我介绍
- 2 = 项目经历
- 3 = 技术提问
- 4 = 代码编程
- 5 = 反问环节
- 6 = 面试结束

【环节推进要求（必须严格执行）】
1) 必须按 0→1→2→3→4→5→6 顺序推进，禁止跳号。
2) 每次回复前先判断当前环节是否完成；候选人每说一句话不代表环节完成。
3) 只有在“当前环节明确完成且不是最后环节”时，才输出推进指令。
4) 推进指令必须放在回复末尾，且逐字一致：
我们进入面试的下一个环节 /next[(下一个环节的编号)]
5) 每次回复最多输出一个 /next[...]。
6) 当前环节未完成时，严禁输出 /next[...]。
7) 到环节 6 时直接结束，不再输出 /next[...]。

【面试流程（7 步）】
步骤0：面试开始
- 简短开场，说明面试将按“自我介绍→项目经历→技术提问→代码编程→反问环节→结束”进行。
- 开场结束后，引导候选人进入自我介绍。

步骤1：自我介绍
- 邀请候选人做 1-2 分钟自我介绍。
- 若候选人信息不足，追问方向、经验与技能要点。

步骤2：项目经历
- 请候选人介绍一个代表性项目，并追问项目目标、职责、关键决策与结果。
- 若有简历信息，优先围绕简历中的项目进行提问。

步骤3：技术提问
- 根据候选人方向提出技术问题（可覆盖基础与工程实践）。
- 关注推理过程、正确性、复杂度与边界意识。

步骤4：代码编程
- 给出一道与候选人方向相关的代码题或实现题。
- 关注思路、实现、鲁棒性、边界条件与测试验证。

步骤5：反问环节
- 询问候选人是否有问题要问面试官。
- 对候选人的问题给出清晰回答。
- 主动告诉候选人请求其反问，而不是等待候选人反问

步骤6：面试结束
- 简短总结候选人表现，礼貌结束面试。

【执行约束】
- 仅围绕当前环节发问，不要提前泄露后续环节内容。
- 不要在候选人尚未回答当前问题时推进。
- 信息不足时先补充提问，再决定是否推进。
- 注意，在每一次对话中，你都必须发出指令，提出问题；你的回复不能是陈述句，必须提出命令化言语或者是问题，以方便候选人回答
"""

# 风格补充：温和型
gentle_style_prompt = """
【风格补充：温和型】
- 语气温柔、理解候选人，鼓励式交流。
- 问题难度以简单到中等为主，循序渐进。
- 每轮追问较少（0-1次），优先给提示再追问。
- 允许候选人逐步修正答案，重点看基础是否扎实。
"""

# 风格补充：正常型
normal_style_prompt = """
【风格补充：正常型】
- 语气专业、客观、中性。
- 问题难度中等并逐步提升。
- 每轮适度追问（1-2次），要求解释思路与复杂度。
- 兼顾正确性、鲁棒性与工程可读性。
"""

# 风格补充：压力型
pressure_style_prompt = """
【风格补充：压力型】
- 面试风格对齐大厂高压技术面：语气克制但强硬、节奏快、标准高，持续要求候选人给出可验证结论。
- 题目难度默认 Medium-Hard 到 Hard，优先考察：边界条件、反例构造、最坏情况、可扩展性与工程权衡。
- 每轮固定"主问题 + 深挖追问"模式：连续追问 3-6 次；候选人若答非所问、跳步、模糊表述，立即要求回到问题并重答。
- 严禁只给结论不讲依据：必须说明推理链、关键不变量/正确性理由，并在必要时给出简短证明思路。
- 必须追问复杂度：时间复杂度、空间复杂度、瓶颈来源、可行优化；若未达到预期复杂度，继续要求替代解法与 trade-off。
- 代码审查必须覆盖鲁棒性：空输入、重复元素、极端规模、越界/溢出、退化场景；至少要求给出 3 个针对性测试用例并解释预期输出。
- 允许在候选人卡住时给极少量方向提示，但不给完整答案；提示后必须立即回收主导权并继续高压追问。
- 输出要求短促直接：每次回复 2-4 句，优先指出漏洞、风险与下一步必须回答的问题。
"""

# 预设系统提示词
PRESET_PROMPTS = {
    "温和型面试官": default_prompt + "\n\n" + gentle_style_prompt,
    "正常型面试官（默认）": default_prompt + "\n\n" + normal_style_prompt,
    "压力型面试官": default_prompt + "\n\n" + pressure_style_prompt,
    "自定义": "",
}


# ==================== 工具函数 ====================
def extract_sentences(text: str) -> tuple[List[str], str]:
    """
    从文本中提取完整句子（以标点符号结尾）
    返回：(完整句子列表, 剩余文本)
    """
    punc_pattern = r'([。！？.!?])'
    parts = re.split(punc_pattern, text)
    
    sentences = []
    i = 0
    while i < len(parts) - 1:
        sentence = parts[i].strip()
        punctuation = parts[i + 1]
        
        if sentence:
            clean_sentence = _strip_markdown(sentence + punctuation)
            if clean_sentence.strip():
                sentences.append(clean_sentence)
        i += 2
    
    remaining = parts[-1].strip() if len(parts) % 2 == 1 else ""
    return sentences, remaining


def extract_next_phase(text: str) -> Optional[int]:
    """
    提取文本中的流程推进标记，例如 /next[3] 或 /next(3)
    返回最后一次出现的阶段编号
    """
    patterns = [
        r'[/\\]next\[\s*(\d+)\s*\]',
        r'[/\\]next\(\s*(\d+)\s*\)',
    ]
    phases: List[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            try:
                phases.append(int(match.group(1)))
            except (ValueError, TypeError):
                continue
    if not phases:
        return None
    return phases[-1]


def strip_next_markers(text: str) -> str:
    """
    移除流程推进标记，避免在前端文本和 TTS 中播报
    """
    cleaned = re.sub(r'[/\\]next\[\s*\d+\s*\]', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'[/\\]next\(\s*\d+\s*\)', '', cleaned, flags=re.IGNORECASE)
    # 清理流式输出中可能出现的不完整标记（例如末尾的 /next[ 或 /next(）
    cleaned = re.sub(r'[/\\]next\s*[\[(][^\])]*$', '', cleaned, flags=re.IGNORECASE)
    # 同时移除流程推进提示语，避免在前端和 TTS 中展示
    control_phrase = '我们进入面试的下一个环节'
    cleaned = re.sub(r'我们进入面试的下一个环节[：:，,。!！?？\s]*', '', cleaned)
    # 避免流式时先显示控制短语前缀、下一帧又被撤回（闪烁）
    # 例如先出现“我们进入”，随后补全成完整控制短语后被清洗。
    for i in range(len(control_phrase) - 1, 0, -1):
        prefix = control_phrase[:i]
        if cleaned.endswith(prefix):
            cleaned = cleaned[:-i]
            break
    # 清理被移除标记后产生的多余空白
    cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


async def generate_tts_audio(text: str) -> Optional[str]:
    """
    生成 TTS 音频并返回 base64 编码
    """
    if not text or not text.strip():
        return None
    
    try:
        tts = EdgeTTS_async(rate="+20%")
        temp_file = TEMP_DIR / f"tts_{uuid.uuid4().hex}.mp3"
        
        success, audio_path = await tts.to_speech_async(text, str(temp_file), use_cache=True)
        
        if success and audio_path and Path(audio_path).exists():
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            # 清理临时文件
            try:
                Path(audio_path).unlink(missing_ok=True)
            except:
                pass
            return base64.b64encode(audio_data).decode("utf-8")
    except Exception as e:
        print(f"TTS 生成失败: {e}")
    
    return None


# ==================== API 端点 ====================

@app.get("/")
async def root():
    """根路径 - 返回前端页面（禁用缓存确保加载最新版本）"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(
            str(index_file),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return {"message": "AI 面试官 API", "version": "2.0.0"}


@app.get("/api/presets")
async def get_presets():
    """获取预设提示词列表"""
    return {
        "presets": list(PRESET_PROMPTS.keys()),
        "prompts": PRESET_PROMPTS
    }


@app.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return session_store["settings"]


@app.post("/api/settings")
async def update_settings(settings: SettingsModel):
    """更新设置"""
    session_store["settings"] = settings.model_dump()
    return {"status": "ok", "settings": session_store["settings"]}


@app.get("/api/history")
async def get_history():
    """获取对话历史"""
    return {"history": session_store["history"]}


@app.delete("/api/history")
async def clear_history():
    """清空对话历史"""
    session_store["history"] = []
    session_store["rag_history"] = []
    return {"status": "ok", "message": "对话历史已清空"}


@app.get("/api/rag/history")
async def get_rag_history():
    """获取 RAG 检索历史"""
    return {"rag_history": session_store["rag_history"]}


@app.get("/api/rag/domains")
async def get_rag_domains():
    """获取可用的 RAG 领域"""
    vdb_root = BASE_DIR / "vector_db"
    domains = []
    if vdb_root.exists():
        domains = sorted([d.name for d in vdb_root.iterdir() if d.is_dir()])
    return {"domains": domains}


# ==================== 简历相关 API ====================

@app.get("/api/resume/status")
async def get_resume_status():
    """获取简历上传状态"""
    return {
        "uploaded": session_store["resume_uploaded"],
        "file_name": session_store["resume_file_name"],
        "analysis": session_store["resume_analysis"]
    }


@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """上传并解析简历 PDF"""
    try:
        # 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "只支持 PDF 文件格式"}
            )
        
        # 保存临时文件
        temp_file = TEMP_DIR / f"resume_{uuid.uuid4().hex}.pdf"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"📄 [简历上传] 文件已保存: {temp_file}")
        
        try:
            # 解析简历
            analysis_result = parse_resume(str(temp_file))
            
            print(f"✅ [简历上传] 解析成功，基本信息: {analysis_result.get('basic_info', {})}")
            
            # 存储到 session
            session_store["resume_uploaded"] = True
            session_store["resume_analysis"] = analysis_result
            session_store["resume_file_name"] = file.filename
            
            print(f"💾 [简历上传] 已存储到 session_store, resume_uploaded={session_store['resume_uploaded']}")
            
            return {
                "status": "ok",
                "message": "简历解析成功",
                "file_name": file.filename,
                "analysis": analysis_result
            }
        finally:
            # 清理临时文件
            try:
                temp_file.unlink(missing_ok=True)
            except:
                pass
    
    except Exception as e:
        print(f"❌ [简历上传] 失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"简历解析失败：{str(e)}"}
        )


@app.delete("/api/resume")
async def delete_resume():
    """删除已上传的简历"""
    session_store["resume_uploaded"] = False
    session_store["resume_analysis"] = None
    session_store["resume_file_name"] = ""
    return {"status": "ok", "message": "简历已删除"}


# ==================== 导师搜索相关 API ====================

@app.get("/api/advisor/status")
async def get_advisor_status():
    """获取导师搜索状态"""
    return {
        "searched": session_store["advisor_searched"],
        "school": session_store["advisor_school"],
        "name": session_store["advisor_name"],
        "info": session_store["advisor_info"]
    }


@app.post("/api/advisor/search")
async def search_advisor(school: str = Form(...), name: str = Form(...)):
    """搜索导师信息"""
    try:
        print(f"🔍 [导师搜索] 开始搜索：{school} - {name}")
        
        # 调用搜索模块
        result = search_advisor_info(school, name)
        
        if result["success"]:
            print(f"✅ [导师搜索] 搜索成功")
            
            # 存储到 session
            session_store["advisor_searched"] = True
            session_store["advisor_info"] = result["data"]
            session_store["advisor_school"] = school
            session_store["advisor_name"] = name
            
            return {
                "status": "ok",
                "message": "导师信息搜索成功",
                "info": result["data"]
            }
        else:
            print(f"❌ [导师搜索] 搜索失败：{result['error']}")
            
            # 搜索失败时，设置为通用模式
            session_store["advisor_searched"] = False
            session_store["advisor_info"] = None
            
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"未找到导师信息：{result['error']}",
                    "fallback": True
                }
            )
    
    except Exception as e:
        print(f"❌ [导师搜索] 异常：{str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"搜索失败：{str(e)}"}
        )


@app.post("/api/advisor/search/stream")
async def search_advisor_stream_api(school: str = Form(...), name: str = Form(...)):
    """流式搜索导师信息，两阶段 + 按优先级渐进返回"""
    
    async def generate():
        try:
            all_results = {}
            
            async for chunk in search_advisor_stream(school, name):
                if chunk["priority"] == "error":
                    yield f"data: {json.dumps({'error': chunk['results'][0]['error']})}\n\n"
                    return
                
                elif chunk["priority"] == "verify":
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk["priority"] == "verified":
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk["priority"] in ["p1", "p2", "p3"]:
                    for r in chunk["results"]:
                        if r["success"]:
                            all_results[r["key"]] = r["data"]
                    
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                elif chunk["priority"] == "done":
                    full_info = chunk["full_info"]
                    
                    session_store["advisor_searched"] = True
                    session_store["advisor_info"] = full_info
                    session_store["advisor_school"] = school
                    session_store["advisor_name"] = name
                    
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
        except Exception as e:
            print(f"❌ [导师流式搜索] 异常：{str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.delete("/api/advisor")
async def delete_advisor():
    """删除已搜索的导师信息"""
    session_store["advisor_searched"] = False
    session_store["advisor_info"] = None
    session_store["advisor_school"] = ""
    session_store["advisor_name"] = ""
    return {"status": "ok", "message": "导师信息已清除"}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天 + 实时 TTS
    返回 SSE 流，包含文本更新和音频数据
    """
    async def generate():
        try:
            # 准备系统提示词
            system_prompt = request.system_prompt
            if not system_prompt:
                settings = session_store["settings"]
                prompt_choice = settings.get("prompt_choice", "正常型面试官（默认）")
                system_prompt = PRESET_PROMPTS.get(prompt_choice, "")
            
            # RAG 检索
            retrieved = ""
            if request.enable_rag:
                try:
                    persist_dir = str(BASE_DIR / "vector_db")
                    retrieved = get_retrieved_context(
                        request.message,
                        domain=request.rag_domain,
                        k=request.rag_top_k,
                        persist_dir=persist_dir,
                    )
                    if retrieved and retrieved.strip():
                        system_prompt += f"\n\n参考知识库内容（仅供回答参考）：\n{retrieved}"
                        session_store["rag_history"].append({
                            "query": request.message,
                            "retrieved": retrieved,
                            "domain": request.rag_domain,
                            "top_k": request.rag_top_k,
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception as e:
                    print(f"RAG 检索失败: {e}")
            
            # 注入简历信息
            print(f"🔍 [聊天] 检查简历状态：uploaded={session_store['resume_uploaded']}, analysis={session_store['resume_analysis'] is not None}")
            if session_store["resume_uploaded"] and session_store["resume_analysis"]:
                resume_info = format_resume_for_prompt(session_store["resume_analysis"])
                system_prompt += (
                    "\n\n【候选人简历信息】\n" + resume_info
                    + "\n\n请根据候选人的背景，调整面试难度和问题方向，个性化面试。"
                )
                print(f"✅ [聊天] 已注入简历信息，长度：{len(resume_info)} 字符")
            else:
                print(f"⚠️ [聊天] 未检测到简历，跳过注入")
            
            # 注入导师信息
            print(f"🔍 [聊天] 检查导师信息状态：searched={session_store['advisor_searched']}, info={session_store['advisor_info'] is not None}")
            if session_store["advisor_searched"] and session_store["advisor_info"]:
                advisor_info_text = format_advisor_info_for_prompt(session_store["advisor_info"])
                system_prompt += (
                    "\n\n【面试导师信息】\n" + advisor_info_text
                    + "\n\n请根据导师的研究方向和学术背景，提出针对性的专业问题，考察候选人与该导师研究方向的匹配度。"
                )
                print(f"✅ [聊天] 已注入导师信息，长度：{len(advisor_info_text)} 字符")
            else:
                print(f"⚠️ [聊天] 未检测到导师信息，使用通用面试流程")
            
            # 更新历史
            history = list(request.history)
            session_store["history"] = history + [{"role": "user", "content": request.message}]
            
            # 流式 LLM 输出 + 实时 TTS
            full_response = ""
            latest_phase: Optional[int] = None
            sentence_buffer = ""
            processed_length = 0
            
            for partial in llm_stream_chat(history, request.message, system_prompt):
                # 后台识别流程推进标记
                phase = extract_next_phase(partial)
                if phase is not None and phase != latest_phase:
                    latest_phase = phase
                    yield f"data: {json.dumps({'type': 'phase', 'phase': phase}, ensure_ascii=False)}\n\n"

                # 对前端显示和 TTS 过滤流程标记
                full_response = strip_next_markers(partial)
                
                # 发送文本更新
                yield f"data: {json.dumps({'type': 'text', 'content': full_response}, ensure_ascii=False)}\n\n"
                
                # 检测新句子并生成 TTS
                if request.enable_tts:
                    if processed_length > len(full_response):
                        processed_length = len(full_response)
                    new_text = full_response[processed_length:]
                    sentence_buffer += new_text
                    processed_length = len(full_response)
                    
                    sentences, sentence_buffer = extract_sentences(sentence_buffer)
                    
                    for sentence in sentences:
                        # 立即生成 TTS 并发送
                        audio_base64 = await generate_tts_audio(sentence)
                        if audio_base64:
                            yield f"data: {json.dumps({'type': 'audio', 'sentence': sentence, 'data': audio_base64}, ensure_ascii=False)}\n\n"
            
            # 处理剩余文本
            if request.enable_tts and sentence_buffer.strip():
                audio_base64 = await generate_tts_audio(sentence_buffer)
                if audio_base64:
                    yield f"data: {json.dumps({'type': 'audio', 'sentence': sentence_buffer, 'data': audio_base64}, ensure_ascii=False)}\n\n"
            
            # 更新历史
            session_store["history"].append({"role": "assistant", "content": full_response})
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'full_response': full_response}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """语音识别"""
    try:
        # 保存上传的音频文件
        temp_file = TEMP_DIR / f"asr_{uuid.uuid4().hex}.wav"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 调用 ASR
        text = await transcribe_file(str(temp_file), STEPFUN_API_KEY)
        
        # 清理临时文件
        try:
            temp_file.unlink(missing_ok=True)
        except:
            pass
        
        if text and text.strip():
            return {"status": "ok", "text": text.strip()}
        else:
            return {"status": "error", "message": "未识别到有效内容"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/report/stream")
async def report_stream():
    """流式生成面试报告"""
    async def generate():
        try:
            history = session_store["history"]
            if not history:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有对话记录'}, ensure_ascii=False)}\n\n"
                return
            
            # 传入简历分析结果
            resume_analysis = session_store.get("resume_analysis", None)
            for partial_report in ai_report_stream(history, resume_analysis=resume_analysis):
                yield f"data: {json.dumps({'type': 'text', 'content': partial_report}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/report/download/{format}")
async def download_report(format: str):
    """下载报告/对话记录"""
    history = session_store["history"]
    
    if format == "json":
        return JSONResponse(
            content=history,
            headers={
                "Content-Disposition": f"attachment; filename=interview_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    elif format == "txt":
        text = _format_history_for_report(history)
        return StreamingResponse(
            iter([text]),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=interview_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            }
        )
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")


# ==================== 代码执行 API ====================
import subprocess
import shutil


async def execute_python(code: str, stdin: str, timeout: int = 10) -> dict:
    """执行 Python 代码"""
    temp_file = TEMP_DIR / f"code_{uuid.uuid4().hex}.py"
    try:
        temp_file.write_text(code, encoding='utf-8')
        result = subprocess.run(
            ['python', str(temp_file)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TEMP_DIR)
        )
        return {
            "status": "ok",
            "output": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "执行超时（限制 10 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        temp_file.unlink(missing_ok=True)


async def execute_javascript(code: str, stdin: str, timeout: int = 10) -> dict:
    """执行 JavaScript 代码 (Node.js)"""
    if not shutil.which('node'):
        return {"status": "error", "message": "未找到 Node.js，请先安装"}
    
    temp_file = TEMP_DIR / f"code_{uuid.uuid4().hex}.js"
    try:
        temp_file.write_text(code, encoding='utf-8')
        result = subprocess.run(
            ['node', str(temp_file)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(TEMP_DIR)
        )
        return {
            "status": "ok",
            "output": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "执行超时（限制 10 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        temp_file.unlink(missing_ok=True)


async def execute_java(code: str, stdin: str, timeout: int = 15) -> dict:
    """执行 Java 代码"""
    if not shutil.which('javac'):
        return {"status": "error", "message": "未找到 javac，请先安装 JDK"}
    
    # 创建临时目录
    temp_dir = TEMP_DIR / f"java_{uuid.uuid4().hex}"
    temp_dir.mkdir(exist_ok=True)
    
    # 提取类名（简单匹配 public class XXX）
    import re
    class_match = re.search(r'public\s+class\s+(\w+)', code)
    class_name = class_match.group(1) if class_match else 'Main'
    
    java_file = temp_dir / f"{class_name}.java"
    try:
        java_file.write_text(code, encoding='utf-8')
        
        # 编译
        compile_result = subprocess.run(
            ['javac', str(java_file)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(temp_dir)
        )
        if compile_result.returncode != 0:
            return {
                "status": "error",
                "message": "编译失败",
                "output": compile_result.stdout,
                "stderr": compile_result.stderr
            }
        
        # 运行
        result = subprocess.run(
            ['java', class_name],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(temp_dir)
        )
        return {
            "status": "ok",
            "output": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "执行超时（限制 15 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


async def execute_cpp(code: str, stdin: str, timeout: int = 15) -> dict:
    """执行 C++ 代码"""
    if not shutil.which('g++'):
        return {"status": "error", "message": "未找到 g++，请先安装"}
    
    temp_dir = TEMP_DIR / f"cpp_{uuid.uuid4().hex}"
    temp_dir.mkdir(exist_ok=True)
    
    cpp_file = temp_dir / "main.cpp"
    exe_file = temp_dir / "main.exe" if os.name == 'nt' else temp_dir / "main"
    
    try:
        cpp_file.write_text(code, encoding='utf-8')
        
        # 编译
        compile_result = subprocess.run(
            ['g++', str(cpp_file), '-o', str(exe_file)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(temp_dir)
        )
        if compile_result.returncode != 0:
            return {
                "status": "error",
                "message": "编译失败",
                "output": compile_result.stdout,
                "stderr": compile_result.stderr
            }
        
        # 运行
        result = subprocess.run(
            [str(exe_file)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(temp_dir)
        )
        return {
            "status": "ok",
            "output": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "执行超时（限制 15 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/code/execute")
async def execute_code(request: CodeExecuteRequest):
    """执行代码 API"""
    code = request.code.strip()
    language = request.language.lower()
    stdin = request.stdin
    
    if not code:
        return {"status": "error", "message": "代码不能为空"}
    
    if language == 'python':
        return await execute_python(code, stdin)
    elif language == 'javascript':
        return await execute_javascript(code, stdin)
    elif language == 'java':
        return await execute_java(code, stdin)
    elif language == 'cpp':
        return await execute_cpp(code, stdin)
    else:
        return {"status": "error", "message": f"不支持的语言: {language}"}


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
