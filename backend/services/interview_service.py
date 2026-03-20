"""
面试服务 - 管理面试流程和状态
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from backend.domain.entities.interview import Interview, InterviewStageDetector
from backend.domain.entities.session import SessionData
from backend.domain.value_objects.interview_stage import InterviewStage
from backend.domain.value_objects.interview_style import InterviewStyle
from backend.domain.interfaces.storage import SessionStorage

logger = logging.getLogger(__name__)


class InterviewService:
    """
    面试服务
    
    管理面试流程、阶段转换和状态维护
    """
    
    def __init__(self, session_store: Optional[SessionStorage] = None):
        """
        初始化面试服务
        
        Args:
            session_store: 会话存储
        """
        self._session_store = session_store
        self._interviews: Dict[str, Interview] = {}
    
    def create_interview(
        self,
        session_id: str,
        style: str = "normal",
        resume_context: str = "",
        advisor_context: str = "",
    ) -> Interview:
        """
        创建新面试
        
        Args:
            session_id: 会话 ID
            style: 面试风格
            resume_context: 简历上下文
            advisor_context: 导师上下文
            
        Returns:
            Interview: 新创建的面试实例
        """
        interview_id = str(uuid.uuid4())
        
        interview = Interview(
            id=interview_id,
            session_id=session_id,
            style=InterviewStyle(style) if style in [s.value for s in InterviewStyle] else InterviewStyle.NORMAL,
            resume_context=resume_context,
            advisor_context=advisor_context,
        )
        
        self._interviews[session_id] = interview
        logger.info(f"Created interview {interview_id} for session {session_id}")
        
        return interview
    
    def get_interview(self, session_id: str) -> Optional[Interview]:
        """获取面试实例"""
        return self._interviews.get(session_id)
    
    def get_or_create_interview(
        self,
        session_id: str,
        **kwargs
    ) -> Interview:
        """获取或创建面试实例"""
        interview = self.get_interview(session_id)
        if interview is None:
            interview = self.create_interview(session_id, **kwargs)
        return interview
    
    def update_stage_from_response(
        self,
        session_id: str,
        response: str,
    ) -> Optional[int]:
        """
        从 AI 回复中检测并更新面试阶段
        
        Args:
            session_id: 会话 ID
            response: AI 回复文本
            
        Returns:
            Optional[int]: 新阶段（如果发生转换）
        """
        interview = self.get_interview(session_id)
        if interview is None:
            return None
        
        detected_stage = InterviewStageDetector.detect_stage_transition(response)
        if detected_stage is not None:
            old_stage = interview.current_stage.value
            if interview.advance_stage(detected_stage):
                logger.info(
                    f"Interview {interview.id} stage changed: "
                    f"{old_stage} -> {detected_stage}"
                )
                return detected_stage
        
        return None
    
    def set_stage(self, session_id: str, stage: int) -> bool:
        """
        手动设置面试阶段
        
        Args:
            session_id: 会话 ID
            stage: 目标阶段
            
        Returns:
            bool: 是否成功
        """
        interview = self.get_interview(session_id)
        if interview is None:
            return False
        
        return interview.advance_stage(stage)
    
    def complete_interview(self, session_id: str) -> Optional[Interview]:
        """
        完成面试
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[Interview]: 完成的面试实例
        """
        interview = self.get_interview(session_id)
        if interview is None:
            return None
        
        interview.complete()
        logger.info(f"Interview {interview.id} completed")
        
        return interview
    
    def get_interview_summary(self, session_id: str) -> Dict[str, Any]:
        """
        获取面试摘要
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Dict: 面试摘要信息
        """
        interview = self.get_interview(session_id)
        if interview is None:
            return {
                "exists": False,
                "session_id": session_id,
            }
        
        return {
            "exists": True,
            "id": interview.id,
            "session_id": interview.session_id,
            "current_stage": interview.current_stage.value,
            "stage_name": interview.current_stage.display_name,
            "style": interview.style.value,
            "is_completed": interview.is_completed(),
            "duration_minutes": interview.get_duration_minutes(),
            "message_count": len(interview.history),
            "started_at": interview.started_at.isoformat(),
            "ended_at": interview.ended_at.isoformat() if interview.ended_at else None,
        }
    
    def build_system_prompt(
        self,
        session_id: str,
        base_prompt: str = "",
        include_resume: bool = True,
        include_advisor: bool = True,
    ) -> str:
        """
        构建系统提示词
        
        Args:
            session_id: 会话 ID
            base_prompt: 基础提示词
            include_resume: 是否包含简历信息
            include_advisor: 是否包含导师信息
            
        Returns:
            str: 完整的系统提示词
        """
        interview = self.get_interview(session_id)
        if interview is None:
            return base_prompt
        
        parts = [base_prompt] if base_prompt else []
        
        # 添加面试阶段信息
        parts.append(f"\n## 当前面试阶段\n{interview.current_stage.display_name}")
        
        # 添加简历信息
        if include_resume and interview.resume_context:
            parts.append(f"\n## 候选人简历信息\n{interview.resume_context}")
        
        # 添加导师信息
        if include_advisor and interview.advisor_context:
            parts.append(f"\n## 目标导师信息\n{interview.advisor_context}")
        
        return "\n".join(parts)
    
    def cleanup_expired_interviews(self, max_age_hours: int = 24) -> int:
        """
        清理过期的面试
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            int: 清理的面试数量
        """
        now = datetime.now()
        expired = []
        
        for session_id, interview in self._interviews.items():
            age_hours = (now - interview.started_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired.append(session_id)
        
        for session_id in expired:
            del self._interviews[session_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired interviews")
        
        return len(expired)
