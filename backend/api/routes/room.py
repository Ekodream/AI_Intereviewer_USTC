"""
API 路由 - 房间（导师端和学生端）
"""

from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ==================== 导师端路由 ====================

teacher_router = APIRouter(prefix="/api/teacher", tags=["teacher"])


class RoomCreateRequest(BaseModel):
    """房间创建请求"""
    teacher_name: str
    config: Dict[str, Any]


@teacher_router.post("/room/create")
async def create_room(request: RoomCreateRequest):
    """创建测试房间"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    try:
        room_id = room_service.create_room(request.teacher_name, request.config)
        return {"status": "ok", "room_id": room_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@teacher_router.get("/rooms")
async def list_rooms():
    """列出所有房间"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    rooms = room_service.list_rooms()
    return {"rooms": rooms}


@teacher_router.get("/room/{room_id}")
async def get_room_detail(room_id: str):
    """获取房间详情"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    room = room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    return room.to_dict()


@teacher_router.put("/room/{room_id}/close")
async def close_room(room_id: str):
    """关闭房间"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    success = room_service.close_room(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="房间不存在")
    return {"status": "ok"}


@teacher_router.get("/room/{room_id}/results")
async def get_room_results(room_id: str):
    """获取房间所有学生结果"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    results = room_service.get_room_results(room_id)
    return {"results": results}


@teacher_router.get("/room/{room_id}/student/{session_id}")
async def get_student_result(room_id: str, session_id: str):
    """获取单个学生详情"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    
    result = room_service.get_student_result(room_id, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="学生结果不存在")
    
    return {
        "session_id": result.session_id,
        "room_id": result.room_id,
        "metadata": result.metadata,
        "conversation": result.conversation,
        "report": result.report,
        "videos": result.videos,
    }


# ==================== 学生端路由 ====================

student_router = APIRouter(prefix="/api/student", tags=["student"])


@student_router.post("/join/{room_id}")
async def join_room(
    room_id: str,
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """学生加入测试房间"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    session_manager = container.get_session_manager()
    
    room = room_service.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    if room.status != "active":
        raise HTTPException(status_code=400, detail="房间已关闭")
    
    # 关联会话到房间
    await session_manager.update(session_id, {
        "room_id": room_id,
        "mode": "test",
        "settings": room.config,
    })
    
    room_service.increment_student_count(room_id)
    
    return {
        "status": "ok",
        "room": room.to_dict(),
        "message": f"已加入房间 {room_id}",
    }


@student_router.post("/submit")
async def submit_test_result(session_id: str = Header(default="default", alias="X-Session-ID")):
    """学生提交测试结果"""
    from backend.container import get_container
    
    container = get_container()
    room_service = container.get_room_service()
    session_manager = container.get_session_manager()
    
    session = await session_manager.get_or_create(session_id)
    room_id = session.get("room_id")
    
    if not room_id:
        raise HTTPException(status_code=400, detail="当前不在测试模式")
    
    # 保存 metadata
    metadata = {
        "session_id": session_id,
        "room_id": room_id,
        "start_time": session.get("start_time"),
        "end_time": datetime.now().isoformat(),
        "total_turns": len(session.get("history", [])),
        "resume_uploaded": session.get("resume_uploaded", False),
        "video_recorded": len(session.get("videos", [])) > 0,
        "config_snapshot": session.get("settings", {}),
    }
    room_service.save_student_result(room_id, session_id, "metadata", metadata)
    
    # 保存对话记录
    room_service.save_student_result(
        room_id,
        session_id,
        "conversation",
        session.get("history", []),
    )
    
    return {"status": "ok", "message": "测试结果已提交"}
