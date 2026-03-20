"""
房间实体 - 定义测试房间的核心数据结构
"""

import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


def generate_room_id(length: int = 6) -> str:
    """生成随机房间号"""
    return ''.join(random.choices(string.digits, k=length))


@dataclass
class RoomConfig:
    """房间配置"""
    # 导师信息
    advisor_name: str = ""
    advisor_school: str = ""
    advisor_department: str = ""
    
    # 面试配置
    style: str = "normal"           # 面试风格
    max_duration_minutes: int = 60  # 最大面试时长
    max_students: int = 100         # 最大学生数
    
    # 功能开关
    tts_enabled: bool = True
    vad_enabled: bool = True
    rag_enabled: bool = True
    video_enabled: bool = False
    
    # 自定义提示词
    custom_prompt: str = ""


@dataclass
class StudentResult:
    """学生测试结果"""
    session_id: str
    student_name: str = ""
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # 面试数据
    conversation: List[Dict[str, str]] = field(default_factory=list)
    current_stage: int = 0
    completed: bool = False
    
    # 评估报告
    report_path: Optional[str] = None
    score: Optional[int] = None
    
    # 视频路径
    video_path: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_duration_minutes(self) -> float:
        """获取测试时长（分钟）"""
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds() / 60
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "student_name": self.student_name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "conversation": self.conversation,
            "current_stage": self.current_stage,
            "completed": self.completed,
            "report_path": self.report_path,
            "score": self.score,
            "video_path": self.video_path,
            "metadata": self.metadata,
        }


@dataclass
class Room:
    """
    测试房间实体
    
    表示一个导师创建的测试房间
    """
    id: str
    
    # 房间配置
    config: RoomConfig = field(default_factory=RoomConfig)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    # 房间状态
    is_active: bool = True
    
    # 学生统计
    student_count: int = 0
    completed_count: int = 0
    
    # 学生结果（session_id -> StudentResult）
    results: Dict[str, StudentResult] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        advisor_name: str,
        advisor_school: str = "",
        **config_kwargs
    ) -> "Room":
        """
        创建新房间
        
        Args:
            advisor_name: 导师姓名
            advisor_school: 导师学校
            **config_kwargs: 其他配置参数
            
        Returns:
            Room: 新创建的房间
        """
        room_id = generate_room_id()
        config = RoomConfig(
            advisor_name=advisor_name,
            advisor_school=advisor_school,
            **config_kwargs
        )
        return cls(id=room_id, config=config)
    
    def add_student(self, session_id: str, student_name: str = "") -> StudentResult:
        """
        添加学生到房间
        
        Args:
            session_id: 会话 ID
            student_name: 学生姓名（可选）
            
        Returns:
            StudentResult: 学生结果对象
        """
        if not self.is_active:
            raise ValueError("Room is closed")
        
        if self.student_count >= self.config.max_students:
            raise ValueError("Room is full")
        
        result = StudentResult(session_id=session_id, student_name=student_name)
        self.results[session_id] = result
        self.student_count += 1
        return result
    
    def complete_student(self, session_id: str, score: Optional[int] = None) -> None:
        """
        标记学生完成测试
        
        Args:
            session_id: 会话 ID
            score: 评分（可选）
        """
        if session_id in self.results:
            self.results[session_id].completed = True
            self.results[session_id].ended_at = datetime.now()
            if score is not None:
                self.results[session_id].score = score
            self.completed_count += 1
    
    def close(self) -> None:
        """关闭房间"""
        self.is_active = False
        self.closed_at = datetime.now()
    
    def get_result(self, session_id: str) -> Optional[StudentResult]:
        """获取学生结果"""
        return self.results.get(session_id)
    
    def get_all_results(self) -> List[StudentResult]:
        """获取所有学生结果"""
        return list(self.results.values())
    
    def get_completion_rate(self) -> float:
        """获取完成率"""
        if self.student_count == 0:
            return 0.0
        return self.completed_count / self.student_count
    
    def get_average_score(self) -> Optional[float]:
        """获取平均分"""
        scores = [r.score for r in self.results.values() if r.score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "config": {
                "advisor_name": self.config.advisor_name,
                "advisor_school": self.config.advisor_school,
                "advisor_department": self.config.advisor_department,
                "style": self.config.style,
                "max_duration_minutes": self.config.max_duration_minutes,
                "max_students": self.config.max_students,
                "tts_enabled": self.config.tts_enabled,
                "vad_enabled": self.config.vad_enabled,
                "rag_enabled": self.config.rag_enabled,
                "video_enabled": self.config.video_enabled,
                "custom_prompt": self.config.custom_prompt,
            },
            "created_at": self.created_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "is_active": self.is_active,
            "student_count": self.student_count,
            "completed_count": self.completed_count,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        """从字典创建"""
        config_data = data.get("config", {})
        config = RoomConfig(
            advisor_name=config_data.get("advisor_name", ""),
            advisor_school=config_data.get("advisor_school", ""),
            advisor_department=config_data.get("advisor_department", ""),
            style=config_data.get("style", "normal"),
            max_duration_minutes=config_data.get("max_duration_minutes", 60),
            max_students=config_data.get("max_students", 100),
            tts_enabled=config_data.get("tts_enabled", True),
            vad_enabled=config_data.get("vad_enabled", True),
            rag_enabled=config_data.get("rag_enabled", True),
            video_enabled=config_data.get("video_enabled", False),
            custom_prompt=config_data.get("custom_prompt", ""),
        )
        
        room = cls(
            id=data.get("id", ""),
            config=config,
            is_active=data.get("is_active", True),
            student_count=data.get("student_count", 0),
            completed_count=data.get("completed_count", 0),
            metadata=data.get("metadata", {}),
        )
        
        if data.get("created_at"):
            room.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("closed_at"):
            room.closed_at = datetime.fromisoformat(data["closed_at"])
        
        return room
