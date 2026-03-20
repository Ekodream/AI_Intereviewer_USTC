"""
API 路由 - 聊天和 ASR 相关
"""

import json
import uuid
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    history: List[Dict[str, str]] = []
    system_prompt: str = ""
    enable_tts: bool = True
    enable_rag: bool = True
    rag_domain: str = "cs ai"
    rag_top_k: int = 6


# ==================== 聊天 API ====================

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """
    流式聊天 + 实时 TTS
    
    返回 SSE 流，包含文本更新和音频数据
    """
    from backend.container import get_container
    
    container = get_container()
    chat_service = container.get_chat_service()
    session_manager = container.get_session_manager()
    
    async def generate():
        try:
            # 获取会话
            session = await session_manager.get_or_create(session_id)
            
            # 准备系统提示词
            system_prompt = request.system_prompt
            if not system_prompt:
                settings = session.get("settings", {})
                from backend.api.dependencies import get_preset_prompt
                system_prompt = get_preset_prompt(settings.get("prompt_choice"))
            
            # 更新历史
            history = list(request.history)
            await session_manager.add_message(session_id, "user", request.message)
            
            full_response = ""
            latest_phase = None
            
            # 流式生成
            async for chunk in chat_service.stream_chat(
                session_id=session_id,
                message=request.message,
                history=history,
                system_prompt=system_prompt,
                enable_rag=request.enable_rag,
                rag_domain=request.rag_domain,
                rag_top_k=request.rag_top_k,
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "text":
                    full_response = chunk["content"]
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "phase":
                    if chunk["phase"] != latest_phase:
                        latest_phase = chunk["phase"]
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
                elif chunk_type == "sentence" and request.enable_tts:
                    # 生成 TTS
                    audio_service = container.get_audio_service()
                    success, audio_base64 = await audio_service.text_to_speech(
                        chunk["content"]
                    )
                    if success and audio_base64:
                        yield f"data: {json.dumps({'type': 'audio', 'sentence': chunk['content'], 'data': audio_base64}, ensure_ascii=False)}\n\n"
            
            # 保存助手回复
            await session_manager.add_message(session_id, "assistant", full_response)
            
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


# ==================== ASR API ====================

@router.post("/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """语音识别"""
    from backend.container import get_container
    from backend.config.settings import get_settings
    
    settings = get_settings()
    container = get_container()
    
    try:
        # 保存临时文件
        temp_file = settings.temp_dir / f"asr_{uuid.uuid4().hex}.wav"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 调用 ASR
        audio_service = container.get_audio_service()
        text = await audio_service.transcribe_file(temp_file)
        
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


# ==================== 历史记录 API ====================

@router.get("/history")
async def get_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取对话历史"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    history = await session_manager.get_history(session_id)
    return {"history": history}


@router.delete("/history")
async def clear_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """清空对话历史"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    await session_manager.clear_history(session_id)
    return {"status": "ok", "message": "对话历史已清空"}


# ==================== RAG API ====================

@router.get("/rag/history")
async def get_rag_history(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取 RAG 检索历史"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    session = await session_manager.get_or_create(session_id)
    return {"rag_history": session.get("rag_history", [])}


@router.get("/rag/domains")
async def get_rag_domains():
    """获取可用的 RAG 领域"""
    from backend.config.settings import get_settings
    
    settings = get_settings()
    vdb_root = settings.vector_db_dir
    
    domains = []
    if vdb_root.exists():
        domains = sorted([d.name for d in vdb_root.iterdir() if d.is_dir()])
    
    return {"domains": domains}
