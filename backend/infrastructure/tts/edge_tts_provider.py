"""
Edge TTS 提供者实现 - 基于微软 Edge TTS 的免费语音合成服务
"""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

from backend.domain.interfaces.tts_provider import TTSProvider
from backend.infrastructure.utils.text_cleaner import strip_markdown


# 中文声音配置
EDGE_VOICES = {
    "zh-CN-YunjianNeural": "云健（男声，沉稳磁性）",
    "zh-CN-YunxiNeural": "云希（男声，年轻活泼）",
    "zh-CN-YunyangNeural": "云扬（男声，新闻播报）",
    "zh-CN-XiaoxiaoNeural": "晓晓（女声，甜美活泼）",
    "zh-CN-XiaoyiNeural": "晓伊（女声，温柔亲切）",
    "zh-CN-XiaochenNeural": "晓辰（女声，温暖）",
}

DEFAULT_VOICE = "zh-CN-YunjianNeural"


class TTSCache:
    """TTS 缓存管理"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "edge_tts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_hash(self, text: str, voice: str, speed: float) -> str:
        """生成缓存键"""
        key = f"{text}|{voice}|{speed}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, text: str, voice: str, speed: float) -> Optional[Path]:
        """获取缓存文件"""
        hash_key = self._get_hash(text, voice, speed)
        cache_file = self.cache_dir / f"{hash_key}.mp3"
        if cache_file.exists() and cache_file.stat().st_size > 0:
            return cache_file
        return None
    
    def set(self, text: str, voice: str, speed: float, audio_path: Path) -> Path:
        """保存到缓存"""
        import shutil
        hash_key = self._get_hash(text, voice, speed)
        cache_file = self.cache_dir / f"{hash_key}.mp3"
        shutil.copy2(audio_path, cache_file)
        return cache_file


class EdgeTTSProvider(TTSProvider):
    """
    Edge TTS 提供者实现
    
    使用微软 Edge 的免费 TTS 服务，无需 API Key
    """
    
    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "+20%",
        volume: str = "+0%",
        cache_enabled: bool = True,
        output_dir: Optional[Path] = None,
    ):
        if not EDGE_TTS_AVAILABLE:
            raise ImportError("edge-tts 未安装，请运行: pip install edge-tts")
        
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.cache_enabled = cache_enabled
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "tts_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cache = TTSCache() if cache_enabled else None
    
    @property
    def provider_name(self) -> str:
        return "Edge TTS"
    
    @property
    def supported_voices(self) -> List[str]:
        return list(EDGE_VOICES.keys())
    
    def _convert_speed(self, speed: float) -> str:
        """将速度倍数转换为 Edge TTS 格式"""
        if speed == 1.0:
            return self.rate
        percent = int((speed - 1.0) * 100)
        return f"+{percent}%" if percent >= 0 else f"{percent}%"
    
    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[Path]]:
        """合成语音文件"""
        try:
            # 清理文本
            clean_text = strip_markdown(text)
            if not clean_text.strip():
                return False, None
            
            use_voice = voice or self.voice
            rate = self._convert_speed(speed)
            
            # 检查缓存
            if self._cache:
                cached = self._cache.get(clean_text, use_voice, speed)
                if cached:
                    return True, cached
            
            # 生成输出路径
            file_hash = hashlib.md5(clean_text.encode()).hexdigest()[:12]
            output_path = self.output_dir / f"tts_{file_hash}.mp3"
            
            # 调用 Edge TTS
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=use_voice,
                rate=rate,
                volume=self.volume,
            )
            await communicate.save(str(output_path))
            
            # 验证生成结果
            if output_path.exists() and output_path.stat().st_size > 0:
                # 保存到缓存
                if self._cache:
                    self._cache.set(clean_text, use_voice, speed, output_path)
                return True, output_path
            
            return False, None
            
        except Exception as e:
            print(f"❌ Edge TTS 生成失败: {e}")
            return False, None
    
    async def synthesize_to_bytes(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[bytes]]:
        """合成语音并返回字节数据"""
        success, path = await self.synthesize(text, voice=voice, speed=speed)
        if success and path:
            try:
                return True, path.read_bytes()
            except Exception:
                pass
        return False, None
    
    @staticmethod
    def get_voice_descriptions() -> dict:
        """获取声音描述"""
        return EDGE_VOICES
    
    @staticmethod
    async def list_all_voices() -> List[dict]:
        """获取所有可用声音（包括其他语言）"""
        if not EDGE_TTS_AVAILABLE:
            return []
        return await edge_tts.list_voices()
