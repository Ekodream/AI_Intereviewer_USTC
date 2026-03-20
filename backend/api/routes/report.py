"""
API 路由 - 报告相关
"""

import json
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse


router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/stream")
async def report_stream(session_id: str = Header(default="default", alias="X-Session-ID")):
    """流式生成面试报告"""
    from backend.container import get_container
    
    container = get_container()
    report_service = container.get_report_service()
    session_manager = container.get_session_manager()
    room_service = container.get_room_service()
    
    async def generate():
        try:
            session = await session_manager.get_or_create(session_id)
            history = session.get("history", [])
            
            if not history:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有对话记录'}, ensure_ascii=False)}\n\n"
                return
            
            # 获取简历分析结果
            resume_analysis = session.get("resume_analysis")
            advisor_links = session.get("advisor_references", [])
            
            final_report = ""
            for partial_report in report_service.generate_report_stream(
                history,
                resume_analysis=resume_analysis,
            ):
                final_report = partial_report
                yield f"data: {json.dumps({'type': 'text', 'content': partial_report}, ensure_ascii=False)}\n\n"
            
            # 追加参考链接
            if advisor_links:
                final_with_links = report_service.append_reference_links(
                    final_report,
                    advisor_links,
                )
                final_report = final_with_links
                yield f"data: {json.dumps({'type': 'text', 'content': final_with_links}, ensure_ascii=False)}\n\n"
            
            # 如果是测试模式，保存报告
            room_id = session.get("room_id")
            if room_id:
                room_service.save_student_result(room_id, session_id, "report", final_report)
            
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


@router.get("/download/{format}")
async def download_report(
    format: str,
    session_id: str = Header(default="default", alias="X-Session-ID"),
):
    """下载报告/对话记录"""
    from backend.container import get_container
    
    container = get_container()
    session_manager = container.get_session_manager()
    report_service = container.get_report_service()
    
    session = await session_manager.get_or_create(session_id)
    history = session.get("history", [])
    
    if format == "json":
        return JSONResponse(
            content=history,
            headers={
                "Content-Disposition": f"attachment; filename=interview_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    elif format == "txt":
        text = report_service.format_history(history)
        return StreamingResponse(
            iter([text]),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=interview_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            }
        )
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")
