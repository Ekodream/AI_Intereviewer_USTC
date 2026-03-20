"""
值对象模块 - 定义不可变的领域值对象
"""

from backend.domain.value_objects.interview_stage import InterviewStage
from backend.domain.value_objects.interview_style import InterviewStyle
from backend.domain.value_objects.audio_config import (
    AudioConfig,
    TTSConfig,
    ASRConfig,
    VADConfig,
)

__all__ = [
    "InterviewStage",
    "InterviewStyle",
    "AudioConfig",
    "TTSConfig",
    "ASRConfig",
    "VADConfig",
]
