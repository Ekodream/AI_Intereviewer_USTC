"""
API 路由 - 导师相关
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/api/advisor", tags=["advisor"])


@router.get("/status")
async def get_advisor_status(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取导师搜索状态"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    session = await session_manager.get_or_create(session_id)
    
    return {
        "mode": session.get("advisor_mode", "ai_default"),
        "searched": session.get("advisor_searched", False),
        "school": session.get("advisor_school", ""),
        "lab": session.get("advisor_lab", ""),
        "name": session.get("advisor_name", ""),
        "info": session.get("advisor_info"),
        "references": session.get("advisor_references", []),
    }


@router.post("/search")
async def search_advisor(
    school: str = Form(""),
    lab: str = Form(""),
    name: str = Form(""),
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """联网搜索导师信息"""
    from backend.container import get_container
    
    container = get_container()
    advisor_service = container.get_advisor_service()
    session_manager = container.get_session_manager()
    
    try:
        result = await advisor_service.search_advisor(
            school=school,
            lab=lab,
            advisor_name=name,
        )
        
        if result["success"]:
            # 更新 session
            await session_manager.update(session_id, {
                "advisor_mode": "custom",
                "advisor_searched": True,
                "advisor_info": result["data"],
                "advisor_references": result.get("references", []),
                "advisor_school": school,
                "advisor_lab": lab,
                "advisor_name": name,
            })
            
            return {
                "status": "ok",
                "message": "导师信息搜索成功",
                "info": result["data"],
                "references": result.get("references", []),
            }
        
        await session_manager.update(session_id, {
            "advisor_searched": False,
            "advisor_info": None,
            "advisor_references": [],
        })
        
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": result.get("error", "未找到导师信息")},
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"搜索失败: {str(e)}"},
        )


@router.delete("")
async def delete_advisor(session_id: str = Header(default="default", alias="X-Session-ID")):
    """清除已搜索导师信息"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    await session_manager.update(session_id, {
        "advisor_mode": "ai_default",
        "advisor_searched": False,
        "advisor_info": None,
        "advisor_references": [],
        "advisor_school": "",
        "advisor_lab": "",
        "advisor_name": "",
    })
    
    return {"status": "ok", "message": "导师信息已清除"}


# ==================== 导师文档 API ====================

@router.post("/document/upload")
async def upload_advisor_document(
    file: UploadFile = File(...),
    advisor_school: str = Form(default=""),
    advisor_lab: str = Form(default=""),
    advisor_name: str = Form(default=""),
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """上传导师相关文档并索引"""
    from backend.container import get_container
    from backend.config.settings import get_settings
    
    settings = get_settings()
    container = get_container()
    session_manager = container.get_session_manager()
    
    try:
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "只支持 PDF 文件格式"}
            )
        
        session = await session_manager.get_or_create(session_id)
        
        # 获取导师信息
        school = advisor_school.strip() or session.get("advisor_school", "")
        lab = advisor_lab.strip() or session.get("advisor_lab", "")
        name = advisor_name.strip() or session.get("advisor_name", "")
        
        if not name and not school:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "请至少提供导师姓名或学校信息"}
            )
        
        # 生成 advisor_id
        id_parts = [p for p in [school, lab, name] if p]
        advisor_id = "_".join(id_parts).replace(" ", "_")
        
        # 保存文件
        advisor_doc_dir = settings.advisor_docs_dir / advisor_id / session_id
        advisor_doc_dir.mkdir(parents=True, exist_ok=True)
        
        file_id = uuid.uuid4().hex[:8]
        safe_filename = f"{file_id}_{file.filename}"
        file_path = advisor_doc_dir / safe_filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # TODO: 索引到 RAG 系统
        
        # 记录到 session
        docs = session.get("advisor_documents", [])
        docs.append({
            "filename": file.filename,
            "safe_filename": safe_filename,
            "path": str(file_path),
            "size": len(content),
            "timestamp": datetime.now().isoformat(),
            "advisor_id": advisor_id,
        })
        await session_manager.update(session_id, {"advisor_documents": docs})
        
        return {
            "status": "ok",
            "message": "文档上传成功",
            "filename": file.filename,
            "size": len(content),
        }
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"文档上传失败: {str(e)}"}
        )


@router.get("/document/list")
async def list_advisor_documents(session_id: str = Header(default="default", alias="X-Session-ID")):
    """获取导师文档列表"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    session = await session_manager.get_or_create(session_id)
    return {"documents": session.get("advisor_documents", [])}


@router.delete("/document/{filename}")
async def delete_advisor_document(
    filename: str,
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """删除导师文档"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    
    try:
        session = await session_manager.get_or_create(session_id)
        docs = session.get("advisor_documents", [])
        doc_to_delete = None
        
        for doc in docs:
            if doc["safe_filename"] == filename:
                doc_to_delete = doc
                break
        
        if not doc_to_delete:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "文档不存在"}
            )
        
        # 删除文件
        file_path = Path(doc_to_delete["path"])
        if file_path.exists():
            file_path.unlink()
        
        # 更新 session
        docs.remove(doc_to_delete)
        await session_manager.update(session_id, {"advisor_documents": docs})
        
        return {"status": "ok", "message": "文档已删除"}
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"删除失败: {str(e)}"}
        )
