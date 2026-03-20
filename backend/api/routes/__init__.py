"""
路由注册 - 将所有路由模块注册到 FastAPI
"""

from fastapi import FastAPI

from backend.api.routes.chat import router as chat_router
from backend.api.routes.resume import router as resume_router
from backend.api.routes.advisor import router as advisor_router
from backend.api.routes.report import router as report_router
from backend.api.routes.room import teacher_router, student_router


def register_routes(app: FastAPI) -> None:
    """注册所有路由到 FastAPI 应用"""
    app.include_router(chat_router)
    app.include_router(resume_router)
    app.include_router(advisor_router)
    app.include_router(report_router)
    app.include_router(teacher_router)
    app.include_router(student_router)
