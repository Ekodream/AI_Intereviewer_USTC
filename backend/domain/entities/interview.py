"""
面试实体 - 定义面试的核心数据结构
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.domain.value_objects.interview_stage import InterviewStage
from backend.domain.value_objects.interview_style import InterviewStyle


@dataclass
class Interview:
    """
    面试实体
    
    表示一次完整的面试过程
    """
    id: str
    session_id: str
    
    # 面试状态
    current_stage: InterviewStage = InterviewStage.START
    style: InterviewStyle = InterviewStyle.NORMAL
    
    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    
    # 对话历史（按阶段分组）
    history: List[Dict[str, str]] = field(default_factory=list)
    stage_histories: Dict[int, List[Dict[str, str]]] = field(default_factory=dict)
    
    # 上下文信息
    resume_context: str = ""
    advisor_context: str = ""
    rag_context: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def advance_stage(self, target_stage: int) -> bool:
        """
        推进面试阶段
        
        Args:
            target_stage: 目标阶段
            
        Returns:
            bool: 是否成功推进
        """
        try:
            new_stage = InterviewStage.from_int(target_stage)
            if self.current_stage.can_advance_to(new_stage):
                # 保存当前阶段的历史
                self.stage_histories[self.current_stage.value] = self.history.copy()
                self.current_stage = new_stage
                return True
        except ValueError:
            pass
        return False
    
    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stage": self.current_stage.value,
        })
    
    def is_completed(self) -> bool:
        """检查面试是否完成"""
        return self.current_stage.is_terminal()
    
    def complete(self) -> None:
        """完成面试"""
        self.current_stage = InterviewStage.END
        self.ended_at = datetime.now()
    
    def get_duration_minutes(self) -> float:
        """获取面试时长（分钟）"""
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds() / 60
    
    def get_stage_messages(self, stage: InterviewStage) -> List[Dict[str, str]]:
        """获取指定阶段的消息"""
        return [
            msg for msg in self.history
            if msg.get("stage") == stage.value
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "current_stage": self.current_stage.value,
            "style": self.style.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "history": self.history,
            "stage_histories": self.stage_histories,
            "resume_context": self.resume_context,
            "advisor_context": self.advisor_context,
            "rag_context": self.rag_context,
            "metadata": self.metadata,
        }


class InterviewStageDetector:
    """
    面试阶段检测器
    
    从 AI 回复中检测阶段转换指令
    """
    
    # 阶段转换标记的正则表达式
    # 支持多种格式：/next[1], /next(1), /next 1, /next1 等
    STAGE_PATTERNS = [
        r'/next\[(\d+)\]',      # /next[1]
        r'/next\((\d+)\)',      # /next(1)
        r'/next\s+(\d+)',       # /next 1
        r'/next(\d+)',          # /next1
        r'【下一阶段[：:]?\s*(\d+)】',  # 【下一阶段：1】
        r'\[stage[：:]?\s*(\d+)\]',    # [stage: 1]
    ]
    
    @classmethod
    def detect_stage_transition(cls, text: str) -> Optional[int]:
        """
        从文本中检测阶段转换
        
        Args:
            text: AI 回复文本
            
        Returns:
            Optional[int]: 目标阶段，未检测到返回 None
        """
        for pattern in cls.STAGE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    stage = int(match.group(1))
                    if 0 <= stage <= 9:
                        return stage
                except (ValueError, IndexError):
                    continue
        return None
    
    @classmethod
    def remove_stage_markers(cls, text: str) -> str:
        """
        移除文本中的阶段标记
        
        Args:
            text: 原始文本
            
        Returns:
            str: 移除标记后的文本
        """
        result = text
        for pattern in cls.STAGE_PATTERNS:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        return result.strip()
