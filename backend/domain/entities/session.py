"""
会话实体 - 定义用户会话的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class Session:
    """
    会话实体
    
    表示一个用户的面试会话，包含会话状态和相关数据
    """
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # 会话元数据
    user_agent: str = ""
    ip_address: str = ""
    
    # 会话状态
    is_active: bool = True
    
    # 关联数据
    interview_id: Optional[str] = None
    room_id: Optional[str] = None
    
    def touch(self) -> None:
        """更新会话访问时间"""
        self.updated_at = datetime.now()
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def deactivate(self) -> None:
        """停用会话"""
        self.is_active = False
        self.updated_at = datetime.now()


@dataclass
class SessionData:
    """
    会话数据
    
    存储会话中的业务数据
    """
    session_id: str
    
    # 对话历史
    history: List[Dict[str, str]] = field(default_factory=list)
    rag_history: List[Dict[str, str]] = field(default_factory=list)
    
    # 简历信息
    resume_uploaded: bool = False
    resume_analysis: Optional[Dict[str, Any]] = None
    resume_context: str = ""
    
    # 导师信息
    advisor_info: Optional[Dict[str, Any]] = None
    advisor_context: str = ""
    
    # 面试设置
    settings: Dict[str, Any] = field(default_factory=lambda: {
        "tts_enabled": True,
        "vad_enabled": True,
        "rag_enabled": True,
        "video_enabled": False,
        "style": "normal",
    })
    
    # 面试状态
    current_stage: int = 0
    stage_history: List[int] = field(default_factory=list)
    
    # 统计信息
    message_count: int = 0
    total_tokens: int = 0
    
    def add_message(self, role: str, content: str) -> None:
        """添加对话消息"""
        self.history.append({"role": role, "content": content})
        self.message_count += 1
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.history.clear()
        self.rag_history.clear()
        self.message_count = 0
        self.current_stage = 0
        self.stage_history.clear()
    
    def update_stage(self, new_stage: int) -> None:
        """更新面试阶段"""
        if new_stage != self.current_stage:
            self.stage_history.append(self.current_stage)
            self.current_stage = new_stage
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "history": self.history,
            "rag_history": self.rag_history,
            "resume_uploaded": self.resume_uploaded,
            "resume_analysis": self.resume_analysis,
            "resume_context": self.resume_context,
            "advisor_info": self.advisor_info,
            "advisor_context": self.advisor_context,
            "settings": self.settings,
            "current_stage": self.current_stage,
            "stage_history": self.stage_history,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """从字典创建"""
        return cls(
            session_id=data.get("session_id", ""),
            history=data.get("history", []),
            rag_history=data.get("rag_history", []),
            resume_uploaded=data.get("resume_uploaded", False),
            resume_analysis=data.get("resume_analysis"),
            resume_context=data.get("resume_context", ""),
            advisor_info=data.get("advisor_info"),
            advisor_context=data.get("advisor_context", ""),
            settings=data.get("settings", {}),
            current_stage=data.get("current_stage", 0),
            stage_history=data.get("stage_history", []),
            message_count=data.get("message_count", 0),
            total_tokens=data.get("total_tokens", 0),
        )
