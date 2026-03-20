"""
StepFun ASR 提供者实现 - 基于 StepFun API 的语音识别服务
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Union, List

from backend.domain.interfaces.asr_provider import ASRProvider


class StepFunASRProvider(ASRProvider):
    """
    StepFun ASR 提供者实现
    
    使用 StepFun 的语音识别 API
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "step-asr",
        timeout: int = 30,
    ):
        """
        初始化 ASR 提供者
        
        Args:
            api_key: StepFun API Key
            model: ASR 模型名称
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.stepfun.com/v1"
    
    @property
    def provider_name(self) -> str:
        return "StepFun ASR"
    
    @property
    def supported_formats(self) -> List[str]:
        return ["wav", "mp3", "m4a", "webm", "ogg"]
    
    @property
    def max_duration_seconds(self) -> int:
        return 300  # 5 分钟
    
    def _read_file_sync(self, path: str) -> Optional[bytes]:
        """同步读取文件"""
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取音频文件失败 {path}: {e}")
            return None
    
    async def transcribe(
        self,
        audio_data: Union[bytes, Path],
        *,
        language: str = "zh",
    ) -> Optional[str]:
        """
        转录音频数据
        
        Args:
            audio_data: 音频字节数据或文件路径
            language: 语言代码
            
        Returns:
            识别的文本，失败返回 None
        """
        try:
            # 如果是路径，读取文件
            if isinstance(audio_data, Path):
                audio_bytes = await asyncio.to_thread(
                    self._read_file_sync, str(audio_data)
                )
                filename = audio_data.name
            else:
                audio_bytes = audio_data
                filename = "audio.wav"
            
            if not audio_bytes:
                return None
            
            # 准备请求
            data = aiohttp.FormData()
            data.add_field('model', self.model)
            data.add_field(
                'file',
                audio_bytes,
                filename=filename,
                content_type='audio/wav'
            )
            data.add_field('language', language)
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                async with session.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        text = result.get('text', '').strip()
                        return text if text else None
                    else:
                        error_text = await response.text()
                        print(f"❌ ASR API 错误 ({response.status}): {error_text}")
                        return None
        
        except asyncio.TimeoutError:
            print("❌ ASR 请求超时")
            return None
        except Exception as e:
            print(f"❌ ASR 转录错误: {e}")
            return None
    
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
            识别的文本，失败返回 None
        """
        if not file_path.exists():
            print(f"❌ 音频文件不存在: {file_path}")
            return None
        
        return await self.transcribe(file_path, language=language)


class ASRFactory:
    """ASR 提供者工厂"""
    
    _default_provider: Optional[ASRProvider] = None
    
    @classmethod
    def create_stepfun(cls, api_key: str, **kwargs) -> ASRProvider:
        """创建 StepFun ASR 提供者"""
        return StepFunASRProvider(api_key, **kwargs)
    
    @classmethod
    def get_default(cls, api_key: Optional[str] = None) -> Optional[ASRProvider]:
        """获取默认提供者"""
        if cls._default_provider is None and api_key:
            cls._default_provider = cls.create_stepfun(api_key)
        return cls._default_provider
    
    @classmethod
    def set_default(cls, provider: ASRProvider) -> None:
        """设置默认提供者"""
        cls._default_provider = provider
