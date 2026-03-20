"""
ASR 提供者接口 - 定义语音识别服务的抽象接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union


class ASRProvider(ABC):
    """
    ASR (语音识别) 提供者抽象基类
    
    定义语音识别服务的标准接口。
    所有 ASR 实现（如 StepFun ASR 等）都必须实现此接口。
    """
    
    @abstractmethod
    async def transcribe(
        self,
        audio_data: Union[bytes, Path],
        *,
        language: str = "zh",
    ) -> Optional[str]:
        """
        将语音转换为文本
        
        Args:
            audio_data: 音频数据（字节或文件路径）
            language: 语言代码，默认中文
            
        Returns:
            Optional[str]: 识别的文本，失败返回 None
        """
        pass
    
    @abstractmethod
    async def transcribe_file(
        self,
        file_path: Path,
        *,
        language: str = "zh",
    ) -> Optional[str]:
        """
        转录音频文件
        
        Args:
            file_path: 音频文件路径
            language: 语言代码
            
        Returns:
            Optional[str]: 识别的文本，失败返回 None
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取提供者名称"""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """获取支持的音频格式列表"""
        pass
    
    @property
    @abstractmethod
    def max_duration_seconds(self) -> int:
        """获取最大支持的音频时长（秒）"""
        pass
