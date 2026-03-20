"""
TTS 提供者接口 - 定义文本转语音服务的抽象接口
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple


class TTSProvider(ABC):
    """
    TTS 提供者抽象基类
    
    定义文本转语音服务的标准接口。
    所有 TTS 实现（如 StepFun、Edge TTS 等）都必须实现此接口。
    """
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[Path]]:
        """
        将文本合成为语音文件
        
        Args:
            text: 要转换的文本
            voice: 语音音色（可选，使用默认值）
            speed: 语速，1.0 为正常速度
            
        Returns:
            Tuple[bool, Optional[Path]]: (是否成功, 音频文件路径)
        """
        pass
    
    @abstractmethod
    async def synthesize_to_bytes(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[bytes]]:
        """
        将文本合成为语音字节数据
        
        Args:
            text: 要转换的文本
            voice: 语音音色（可选）
            speed: 语速
            
        Returns:
            Tuple[bool, Optional[bytes]]: (是否成功, 音频字节数据)
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """获取提供者名称"""
        pass
    
    @property
    @abstractmethod
    def supported_voices(self) -> list[str]:
        """获取支持的音色列表"""
        pass


class StreamingTTSProvider(TTSProvider):
    """
    流式 TTS 提供者抽象基类
    
    扩展 TTSProvider，支持流式 TTS 生成（边生成边返回）
    """
    
    @abstractmethod
    async def add_text(self, text: str, priority: int = 0) -> None:
        """
        添加文本到生成队列
        
        Args:
            text: 要转换的文本
            priority: 优先级，数值越大越优先
        """
        pass
    
    @abstractmethod
    async def get_next_audio(self) -> Optional[Tuple[str, bytes]]:
        """
        获取下一个生成完成的音频
        
        Returns:
            Optional[Tuple[str, bytes]]: (文本, 音频数据) 或 None（队列为空）
        """
        pass
    
    @abstractmethod
    def clear_queue(self) -> None:
        """清空生成队列"""
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """获取当前队列大小"""
        pass
