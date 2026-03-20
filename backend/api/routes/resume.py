"""
API 路由 - 简历相关
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.get("/status")
async def get_resume_status(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取简历上传状态"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    session = await session_manager.get_or_create(session_id)
    
    return {
        "uploaded": session.get("resume_uploaded", False),
        "file_name": session.get("resume_file_name", ""),
        "analysis": session.get("resume_analysis"),
    }


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """上传并解析简历 PDF"""
    from backend.container import get_container
    from backend.config.settings import get_settings
    
    settings = get_settings()
    container = get_container()
    resume_service = container.get_resume_service()
    session_manager = container.get_session_manager()
    
    try:
        # 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "只支持 PDF 文件格式"}
            )
        
        # 保存临时文件
        temp_file = settings.temp_dir / f"resume_{uuid.uuid4().hex}.pdf"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # 解析简历
            analysis = await resume_service.parse_resume(temp_file)
            
            # 存储到 session
            await session_manager.update(session_id, {
                "resume_uploaded": True,
                "resume_analysis": analysis.to_dict(),
                "resume_file_name": file.filename,
            })
            
            return {
                "status": "ok",
                "message": "简历解析成功",
                "file_name": file.filename,
                "analysis": analysis.to_dict(),
            }
        finally:
            # 清理临时文件
            try:
                temp_file.unlink(missing_ok=True)
            except:
                pass
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"简历解析失败：{str(e)}"}
        )


@router.delete("")
async def delete_resume(session_id: str = Header(default="default", alias="X-Session-ID")):
    """删除已上传的简历"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    await session_manager.update(session_id, {
        "resume_uploaded": False,
        "resume_analysis": None,
        "resume_file_name": "",
    })
    
    return {"status": "ok", "message": "简历已删除"}
