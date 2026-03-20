"""
音频配置值对象 - 定义音频处理相关的配置
"""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class AudioConfig:
    """
    音频配置值对象
    
    不可变的音频配置，用于 TTS 和 ASR 服务
    """
    sample_rate: int = 16000
    channels: int = 1
    format: str = "mp3"
    
    def __post_init__(self):
        """验证配置值"""
        if self.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError(f"Unsupported sample rate: {self.sample_rate}")
        if self.channels not in [1, 2]:
            raise ValueError(f"Unsupported channels: {self.channels}")


@dataclass(frozen=True)
class TTSConfig:
    """
    TTS 配置值对象
    
    定义文本转语音的配置参数
    """
    provider: Literal["stepfun", "edge"] = "stepfun"
    model: str = "step-tts-mini"
    voice: str = "cixingnansheng"
    speed: float = 1.0
    volume: float = 1.0
    
    # Edge TTS 专用配置
    edge_voice: str = "zh-CN-YunxiNeural"  # 男声
    edge_voice_female: str = "zh-CN-XiaoxiaoNeural"  # 女声
    
    def __post_init__(self):
        """验证配置值"""
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError(f"Speed must be between 0.5 and 2.0, got {self.speed}")
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {self.volume}")


@dataclass(frozen=True)
class ASRConfig:
    """
    ASR 配置值对象
    
    定义语音识别的配置参数
    """
    provider: Literal["stepfun"] = "stepfun"
    model: str = "step-asr"
    language: str = "zh"
    
    # 音频格式要求
    supported_formats: tuple = ("wav", "mp3", "m4a", "webm", "ogg")
    max_duration_seconds: int = 300  # 最大音频时长（秒）
    
    def is_format_supported(self, format: str) -> bool:
        """检查音频格式是否支持"""
        return format.lower() in self.supported_formats


@dataclass(frozen=True)
class VADConfig:
    """
    VAD (语音活动检测) 配置值对象
    
    定义语音活动检测的配置参数
    """
    # 音量阈值
    silence_threshold: float = 0.03
    speech_threshold: float = 0.03
    
    # 时间配置（毫秒）
    silence_duration_ms: int = 1500     # 静音持续时间触发停止
    speech_min_duration_ms: int = 100   # 最小说话时长
    
    # 超时配置（秒）
    no_speech_timeout_seconds: int = 10  # 无语音超时时间
    
    def __post_init__(self):
        """验证配置值"""
        if not 0.0 <= self.silence_threshold <= 1.0:
            raise ValueError(f"Silence threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.speech_threshold <= 1.0:
            raise ValueError(f"Speech threshold must be between 0.0 and 1.0")
