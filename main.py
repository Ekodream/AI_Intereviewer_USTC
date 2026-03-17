# -*- coding: utf-8 -*-
"""
AI Lab-InterReviewer - FastAPI 后端
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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
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
    VIDEOS_DIR,
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
from modules.advisor_search import search_advisor_info, format_advisor_info_for_prompt

# 初始化目录
init_directories()

# ==================== FastAPI 应用 ====================
app = FastAPI(title="AI Lab-InterReviewer", version="2.0.0")

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
    rag_domain: str = "cs ai"
    rag_top_k: int = 6


class SettingsModel(BaseModel):
    prompt_choice: str = "正常型导师（默认）"
    system_prompt: str = ""
    enable_tts: bool = True
    auto_vad: bool = True
    enable_rag: bool = True
    rag_domain: str = "cs ai"
    rag_top_k: int = 6
    compact_mode: bool = False  # 精简对话模式
    advisor_mode: str = "ai_default"  # ai_default | custom
    advisor_school: str = ""
    advisor_lab: str = ""
    advisor_name: str = ""


class CodeExecuteRequest(BaseModel):
    """代码执行请求模型"""
    code: str
    language: str  # python, javascript, java, cpp
    stdin: str = ""


# ==================== 多用户会话管理 ====================
SESSION_TTL_HOURS = 2  # 会话超时时间（小时）
sessions: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    """获取或创建指定 session_id 的用户会话数据，保证用户间数据完全隔离。"""
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "rag_history": [],
            "settings": SettingsModel().model_dump(),
            "resume_uploaded": False,
            "resume_analysis": None,
            "resume_file_name": "",
            "advisor_searched": False,
            "advisor_info": None,
            "advisor_references": [],
            "advisor_school": "",
            "advisor_lab": "",
            "advisor_name": "",
            "advisor_mode": "ai_default",
            "videos": [],
            "last_active": datetime.now(),
        }
    else:
        sessions[session_id]["last_active"] = datetime.now()
    return sessions[session_id]


@app.on_event("startup")
async def start_session_cleanup():
    """应用启动时启动后台会话清理任务。"""
    asyncio.create_task(cleanup_sessions())


async def cleanup_sessions():
    """定期清理超时会话，释放内存。每 30 分钟运行一次。"""
    while True:
        await asyncio.sleep(1800)
        cutoff = datetime.now() - timedelta(hours=SESSION_TTL_HOURS)
        expired = [sid for sid, s in list(sessions.items()) if s["last_active"] < cutoff]
        for sid in expired:
            del sessions[sid]
        if expired:
            print(f"🧹 [会话清理] 已清理 {len(expired)} 个过期会话，当前活跃会话数: {len(sessions)}")

# 预设系统提示词 - 10 阶段流程（保留三种面试风格）
default_prompt = """
你是一位 AI Lab 面试导师。请严格按照以下 10 个环节完成一轮面试，并在每一步只做当前环节的事。

【总体要求】
1) 全程问答式推进，一次只提一个核心问题，不要提太多问题，1-2个即可，确保提问精简。
2) 每次回复简洁、清晰、可执行，不要使用表情符号。
3) 重点考察：理论基础、工程实践、科研动机、论文理解、临场思考与沟通表达。
4) 候选人回答不清晰时，先追问澄清，不要提前进入下一阶段。

【10 个环节与编号（一一对应）】
- 0 = 开始
- 1 = 自我介绍
- 2 = 经历深挖
- 3 = 基础知识
- 4 = 代码
- 5 = 科研动机
- 6 = 科研潜力
- 7 = 综合追问
- 8 = 学生反问
- 9 = 结束

【环节推进要求（必须严格执行）】
1) 必须按 0→1→2→3→4→5→6→7→8→9 顺序推进，禁止跳号。
2) 每次回复前先判断当前阶段是否完成；候选人每说一句话不代表阶段完成。
3) 只有在“当前阶段明确完成且不是最后阶段”时，才输出推进指令。
4) 推进指令必须放在回复末尾，且逐字一致：
我们进入面试的下一个环节 /next[(下一个环节的编号)]
5) 每次回复最多输出一个 /next[...]。
6) 当前阶段未完成时，严禁输出 /next[...]。
7) 到阶段 9 时直接结束，不再输出 /next[...]。

【面试流程（10 步）】
步骤0：开始
- 简短开场，说明面试将按“自我介绍→经历深挖→基础知识→代码→科研动机→科研潜力→综合追问→学生反问→结束”进行。
- 开场结束后，引导候选人进入自我介绍。

步骤1：自我介绍
- 邀请候选人进行结构化自我介绍。
- 若候选人信息不足，追问方向、课程基础、项目与技能要点。
- 此部分结束后进入下一部分。

步骤2：经历深挖
- 请候选人介绍一个代表性经历，并追问目标、职责、关键决策与结果。
- 若有简历信息，优先围绕简历中的项目或研究经历提问。
- 此部分结束后进入下一部分。

步骤3：基础知识
- 根据候选人方向提出基础问题（数学、模型理解、工程基础均可覆盖）。
- 关注推理过程、正确性、复杂度与边界意识。
- 此部分结束后进入下一部分。

步骤4：代码
- 给出一道与候选人方向相关的中等难度代码题，明确输入输出与约束，不要求完善所有细节，可以要求完成一个函数或是代码补全。
- 要求候选人先说明思路，再给出可运行实现；可追问复杂度、边界用例与鲁棒性。
- 鼓励候选人在 IDE 中现场编写并解释关键代码。
- 此部分结束后进入下一部分。

步骤5：科研动机
- 评估候选人选择方向的原因、持续投入意愿、问题意识与学习路径。
- 此部分结束后进入下一部分。

步骤6：科研潜力
- 引导候选人讨论一篇论文或一个研究问题，考察批判性分析与可延展思考。
- 此部分结束后进入下一部分。

步骤7：综合追问
- 给出开放式场景题，要求候选人兼顾理论与工程给出可执行方案。
- 此部分结束后进入下一部分。

步骤8：学生反问
- 主动邀请候选人反问，不要被动等待。
- 对候选人的问题给出清晰、具体、可操作的回答。
- 此部分结束后进入下一部分。

步骤9：结束
- 简短总结候选人表现，礼貌结束面试。

【执行约束】
- 仅围绕当前阶段发问，不要提前泄露后续阶段内容。
- 不要在候选人尚未回答当前问题时推进。
- 信息不足时先补充提问，再决定是否推进。
- 注意，在每一次对话中，你都必须发出指令，提出问题；你的回复不能是纯陈述句，必须包含问题或命令化引导，以方便候选人回答。
- 每次结束后，必须问出问题或给出指令，不允许回复陈述句！
"""

# 风格补充：温和型
gentle_style_prompt = """
【风格补充：温和型】
- 导师风格温和、耐心、鼓励表达，重点帮助候选人呈现研究兴趣与成长轨迹。
- 提问从易到中等，先澄清背景和动机，再逐步引导到方法、实验与反思。
- 每轮追问较少（0-1次），可先给方向性提示，再邀请候选人补充细节。
- 允许候选人逐步修正回答，重点考察学习能力、科研素养与可塑性。
"""

# 风格补充：正常型
normal_style_prompt = """
【风格补充：正常型】
- 导师风格专业、客观、中性，兼顾学术判断与培养视角。
- 问题难度中等并逐步提升，覆盖课程基础、项目经历与科研方法意识。
- 每轮适度追问（1-2次），要求说明问题定义、技术路线、实验设计与结论可靠性。
- 重点评估理论基础、研究潜力、执行能力与沟通清晰度。
"""

# 风格补充：压力型
pressure_style_prompt = """
【风格补充：压力型】
- 导师风格严格、节奏快、标准高，重点检验候选人在科研讨论中的抗压表达与严谨性。
- 题目难度默认中高到高，优先考察：研究问题拆解、假设合理性、方法边界、实验可复现性与失败分析。
- 每轮采用"主问题 + 深挖追问"模式：连续追问 2-4 次；若回答模糊、跳步或缺证据，立即要求回到核心问题并重述。
- 严禁只给结论：必须给出推理链、关键依据、对照实验或可验证证据来源。
- 必须追问方法可信度：评价指标选择、数据划分、偏差来源、统计显著性与泛化风险；必要时要求提出替代方案与权衡。
- 分析需覆盖学术规范：数据与实验伦理、引用与复现规范、工作量评估与里程碑可执行性。
- 允许在候选人卡住时给极少量方向提示，但不给完整答案；提示后继续推进高标准追问。
- 输出要求短促直接：每次回复 2-4 句，优先指出薄弱点并给出必须补充的关键问题。
"""

# 预设系统提示词
PRESET_PROMPTS = {
    "温和型导师": default_prompt + "\n\n" + gentle_style_prompt,
    "正常型导师（默认）": default_prompt + "\n\n" + normal_style_prompt,
    "压力型导师": default_prompt + "\n\n" + pressure_style_prompt,
    "自定义": "",
}

PROMPT_CHOICE_ALIASES = {
    "温和型": "温和型导师",
    "正常型（默认）": "正常型导师（默认）",
    "正常型导师": "正常型导师（默认）",
    "压力型": "压力型导师",
}


def normalize_prompt_choice(choice: Optional[str]) -> str:
    """将历史 prompt 选项兼容映射为统一的导师命名。"""
    legacy_role = "面试" + "官"
    normalized = (choice or "").strip().replace(legacy_role, "导师")
    normalized = PROMPT_CHOICE_ALIASES.get(normalized, normalized)
    if normalized in PRESET_PROMPTS:
        return normalized
    return "正常型导师（默认）"

DEFAULT_AI_ADVISOR_PROMPT = """
【导师信息】
当前使用默认 AI 导师模式。
请按既定面试流程与评分标准推进，不依赖具体真人导师画像。
"""


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
    control_phrases = [
        '我们进入面试的下一个环节',
        '我们进行下一部分',
    ]
    for phrase in control_phrases:
        cleaned = re.sub(re.escape(phrase) + r'[：:，,。!！?？\s]*', '', cleaned)
    # 避免流式时先显示控制短语前缀、下一帧又被撤回（闪烁）
    # 例如先出现“我们进入”，随后补全成完整控制短语后被清洗。
    for phrase in control_phrases:
        for i in range(len(phrase) - 1, 0, -1):
            prefix = phrase[:i]
            if cleaned.endswith(prefix):
                cleaned = cleaned[:-i]
                break
    # 清理被移除标记后产生的多余空白
    cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


def append_advisor_reference_links(report_text: str, links: List[str]) -> str:
    """在报告末尾追加导师搜索参考链接。"""
    if not links:
        return report_text

    deduped_links = []
    seen = set()
    for link in links:
        link = (link or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        deduped_links.append(link)
    deduped_links = deduped_links[:12]

    if not deduped_links:
        return report_text

    lines = [
        "",
        "---",
        "",
        "## 附录：导师搜索参考链接",
        "以下链接来自导师信息联网搜索阶段，供你复核和延伸阅读：",
    ]
    for idx, link in enumerate(deduped_links, start=1):
        lines.append(f"{idx}. {link}")

    return (report_text or "").rstrip() + "\n" + "\n".join(lines) + "\n"


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
    return {"message": "AI Lab-InterReviewer API", "version": "2.0.0"}


@app.get("/api/presets")
async def get_presets():
    """获取预设提示词列表"""
    return {
        "presets": list(PRESET_PROMPTS.keys()),
        "prompts": PRESET_PROMPTS
    }


@app.get("/api/settings")
async def get_settings(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取当前设置"""
    return get_session(session_id)["settings"]


@app.post("/api/settings")
async def update_settings(settings: SettingsModel, session_id: str = Header(default="default", alias="X-Session-ID")):
    """更新设置"""
    settings.prompt_choice = normalize_prompt_choice(settings.prompt_choice)
    get_session(session_id)["settings"] = settings.model_dump()
    # 同步导师设置，便于后端在聊天时直接读取
    get_session(session_id)["advisor_mode"] = settings.advisor_mode
    get_session(session_id)["advisor_school"] = settings.advisor_school
    get_session(session_id)["advisor_lab"] = settings.advisor_lab
    get_session(session_id)["advisor_name"] = settings.advisor_name
    return {"status": "ok", "settings": get_session(session_id)["settings"]}


@app.get("/api/history")
async def get_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取对话历史"""
    return {"history": get_session(session_id)["history"]}


@app.delete("/api/history")
async def clear_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """清空对话历史"""
    get_session(session_id)["history"] = []
    get_session(session_id)["rag_history"] = []
    return {"status": "ok", "message": "对话历史已清空"}


@app.get("/api/rag/history")
async def get_rag_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取 RAG 检索历史"""
    return {"rag_history": get_session(session_id)["rag_history"]}


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
async def get_resume_status(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取简历上传状态"""
    return {
        "uploaded": get_session(session_id)["resume_uploaded"],
        "file_name": get_session(session_id)["resume_file_name"],
        "analysis": get_session(session_id)["resume_analysis"]
    }


@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...), session_id: str = Header(default="default", alias="X-Session-ID")):
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
            get_session(session_id)["resume_uploaded"] = True
            get_session(session_id)["resume_analysis"] = analysis_result
            get_session(session_id)["resume_file_name"] = file.filename
            
            print(f"\U0001f4be [简历上传] 已存储到会话 {session_id[:8]}..., resume_uploaded={get_session(session_id)['resume_uploaded']}")
            
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
async def delete_resume(session_id: str = Header(default="default", alias="X-Session-ID")):
    """删除已上传的简历"""
    get_session(session_id)["resume_uploaded"] = False
    get_session(session_id)["resume_analysis"] = None
    get_session(session_id)["resume_file_name"] = ""
    return {"status": "ok", "message": "简历已删除"}


# ==================== 导师搜索相关 API ====================

@app.get("/api/advisor/status")
async def get_advisor_status(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取导师搜索状态"""
    return {
        "mode": get_session(session_id).get("advisor_mode", "ai_default"),
        "searched": get_session(session_id)["advisor_searched"],
        "school": get_session(session_id)["advisor_school"],
        "lab": get_session(session_id)["advisor_lab"],
        "name": get_session(session_id)["advisor_name"],
        "info": get_session(session_id)["advisor_info"],
        "references": get_session(session_id).get("advisor_references", []),
    }


@app.post("/api/advisor/search")
async def search_advisor(school: str = Form(...), lab: str = Form(...), name: str = Form(...), session_id: str = Header(default="default", alias="X-Session-ID")):
    """联网搜索导师信息"""
    try:
        print(f"🔍 [导师搜索] 开始搜索: {school} | {lab} | {name}")

        result = search_advisor_info(school=school, lab=lab, advisor_name=name)
        if result["success"]:
            get_session(session_id)["advisor_mode"] = "custom"
            get_session(session_id)["advisor_searched"] = True
            get_session(session_id)["advisor_info"] = result["data"]
            get_session(session_id)["advisor_references"] = result.get("references", [])
            get_session(session_id)["advisor_school"] = school
            get_session(session_id)["advisor_lab"] = lab
            get_session(session_id)["advisor_name"] = name

            settings = get_session(session_id).get("settings", {})
            settings.update({
                "advisor_mode": "custom",
                "advisor_school": school,
                "advisor_lab": lab,
                "advisor_name": name,
            })
            get_session(session_id)["settings"] = settings

            return {
                "status": "ok",
                "message": "导师信息搜索成功",
                "info": result["data"],
                "references": result.get("references", []),
            }

        get_session(session_id)["advisor_searched"] = False
        get_session(session_id)["advisor_info"] = None
        get_session(session_id)["advisor_references"] = []
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": result.get("error", "未找到导师信息")},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"搜索失败: {str(e)}"},
        )


@app.delete("/api/advisor")
async def delete_advisor(session_id: str = Header(default="default", alias="X-Session-ID")):
    """清除已搜索导师信息，并回退到默认 AI 导师"""
    get_session(session_id)["advisor_mode"] = "ai_default"
    get_session(session_id)["advisor_searched"] = False
    get_session(session_id)["advisor_info"] = None
    get_session(session_id)["advisor_references"] = []
    get_session(session_id)["advisor_school"] = ""
    get_session(session_id)["advisor_lab"] = ""
    get_session(session_id)["advisor_name"] = ""

    settings = get_session(session_id).get("settings", {})
    settings.update({
        "advisor_mode": "ai_default",
        "advisor_school": "",
        "advisor_lab": "",
        "advisor_name": "",
    })
    get_session(session_id)["settings"] = settings
    return {"status": "ok", "message": "导师信息已清除，已切换为默认 AI 导师"}


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, session_id: str = Header(default="default", alias="X-Session-ID")):
    """
    流式聊天 + 实时 TTS
    返回 SSE 流，包含文本更新和音频数据
    """
    async def generate():
        try:
            # 准备系统提示词
            system_prompt = request.system_prompt
            if not system_prompt:
                settings = get_session(session_id)["settings"]
                prompt_choice = normalize_prompt_choice(settings.get("prompt_choice"))
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
                        get_session(session_id)["rag_history"].append({
                            "query": request.message,
                            "retrieved": retrieved,
                            "domain": request.rag_domain,
                            "top_k": request.rag_top_k,
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception as e:
                    print(f"RAG 检索失败: {e}")
            
            # 注入简历信息
            print(f"🔍 [聊天] 检查简历状态: uploaded={get_session(session_id)['resume_uploaded']}, analysis={get_session(session_id)['resume_analysis'] is not None}")
            if get_session(session_id)["resume_uploaded"] and get_session(session_id)["resume_analysis"]:
                resume_info = format_resume_for_prompt(get_session(session_id)["resume_analysis"])
                system_prompt += (
                    "\n\n【候选人简历信息】\n" + resume_info
                    + "\n\n请根据候选人的背景，调整面试难度和问题方向，个性化面试。"
                )
                print(f"✅ [聊天] 已注入简历信息，长度: {len(resume_info)} 字符")
            else:
                print(f"⚠️ [聊天] 未检测到简历，跳过注入")

            # 注入导师信息（默认 AI 导师；自定义模式且搜索成功后注入联网结果）
            advisor_mode = get_session(session_id).get("advisor_mode", "ai_default")
            advisor_ready = get_session(session_id).get("advisor_searched", False) and bool(get_session(session_id).get("advisor_info"))
            if advisor_mode == "custom" and advisor_ready:
                advisor_info = format_advisor_info_for_prompt(
                    advisor_text=get_session(session_id).get("advisor_info", ""),
                    school=get_session(session_id).get("advisor_school", ""),
                    lab=get_session(session_id).get("advisor_lab", ""),
                    advisor_name=get_session(session_id).get("advisor_name", ""),
                )
                system_prompt += (
                    "\n\n" + advisor_info
                    + "\n\n请根据上述导师信息，在不破坏既定面试流程的前提下，适度提高与导师研究方向相关的追问比例。"
                )
                print("✅ [聊天] 已注入自定义导师信息")
            else:
                system_prompt += "\n\n" + DEFAULT_AI_ADVISOR_PROMPT
                print("ℹ️ [聊天] 使用默认 AI 导师模式")
            
            # 更新历史
            history = list(request.history)
            get_session(session_id)["history"] = history + [{"role": "user", "content": request.message}]
            
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
            get_session(session_id)["history"].append({"role": "assistant", "content": full_response})
            
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
async def report_stream(session_id: str = Header(default="default", alias="X-Session-ID")):
    """流式生成面试报告"""
    async def generate():
        try:
            history = get_session(session_id)["history"]
            if not history:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有对话记录'}, ensure_ascii=False)}\n\n"
                return
            
            # 传入简历分析结果
            resume_analysis = get_session(session_id).get("resume_analysis", None)
            advisor_links = get_session(session_id).get("advisor_references", [])
            final_report = ""
            for partial_report in ai_report_stream(history, resume_analysis=resume_analysis):
                final_report = partial_report
                yield f"data: {json.dumps({'type': 'text', 'content': partial_report}, ensure_ascii=False)}\n\n"

            # 在最终报告末尾追加导师搜索阶段提取到的参考链接
            if advisor_links:
                final_with_links = append_advisor_reference_links(final_report, advisor_links)
                yield f"data: {json.dumps({'type': 'text', 'content': final_with_links}, ensure_ascii=False)}\n\n"
            
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
async def download_report(format: str, session_id: str = Header(default="default", alias="X-Session-ID")):
    """下载报告/对话记录"""
    history = get_session(session_id)["history"]
    
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
    """执行 Python 代码（每次使用独立临时子目录，防止用户间文件干扰）"""
    temp_dir = TEMP_DIR / f"py_{uuid.uuid4().hex}"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / "main.py"
    try:
        temp_file.write_text(code, encoding='utf-8')
        result = subprocess.run(
            ['python', str(temp_file)],
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
        return {"status": "error", "message": "执行超时（限制 10 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def execute_javascript(code: str, stdin: str, timeout: int = 10) -> dict:
    """执行 JavaScript 代码 (Node.js)（每次使用独立临时子目录，防止用户间文件干扰）"""
    if not shutil.which('node'):
        return {"status": "error", "message": "未找到 Node.js，请先安装"}
    
    temp_dir = TEMP_DIR / f"js_{uuid.uuid4().hex}"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / "main.js"
    try:
        temp_file.write_text(code, encoding='utf-8')
        result = subprocess.run(
            ['node', str(temp_file)],
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
        return {"status": "error", "message": "执行超时（限制 10 秒）"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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


# ==================== 视频录制 API ====================

@app.post("/api/video/upload")
async def upload_video(file: UploadFile = File(...), session_id: str = Header(default="default", alias="X-Session-ID")):
    """上传面试视频片段"""
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        video_filename = f"interview_{timestamp}_{uuid.uuid4().hex[:8]}.webm"
        video_path = VIDEOS_DIR / video_filename

        # 保存视频文件
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 记录到 session
        get_session(session_id)["videos"].append({
            "filename": video_filename,
            "path": str(video_path),
            "timestamp": datetime.now().isoformat(),
            "size": len(content)
        })

        print(f"📹 [视频上传] 保存成功: {video_filename}, 大小: {len(content) / 1024:.1f}KB")

        return {
            "status": "ok",
            "message": "视频上传成功",
            "filename": video_filename,
            "size": len(content)
        }
    except Exception as e:
        print(f"❌ [视频上传] 失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"视频上传失败: {str(e)}"}
        )


@app.get("/api/video/list")
async def list_videos(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取已录制的视频列表"""
    return {"videos": get_session(session_id).get("videos", [])}


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
