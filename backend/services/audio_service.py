"""
音频服务 - 处理 TTS 和 ASR 相关业务逻辑
"""

import base64
import asyncio
from pathlib import Path
from typing import Optional, Tuple, AsyncIterator, List
from dataclasses import dataclass

from backend.domain.interfaces.tts_provider import TTSProvider
from backend.domain.interfaces.asr_provider import ASRProvider
from backend.infrastructure.utils.text_cleaner import extract_sentences


@dataclass
class TTSResult:
    """TTS 结果"""
    success: bool
    sentence: str
    audio_base64: Optional[str] = None
    audio_path: Optional[Path] = None


class AudioService:
    """
    音频服务
    
    统一管理 TTS 和 ASR 功能，提供高层业务接口
    """
    
    def __init__(
        self,
        tts_provider: TTSProvider,
        asr_provider: Optional[ASRProvider] = None,
    ):
        self.tts = tts_provider
        self.asr = asr_provider
    
    # ==================== TTS 功能 ====================
    
    async def text_to_speech(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[str]]:
        """
        将文本转换为语音并返回 base64 编码
        
        Args:
            text: 要转换的文本
            voice: 语音音色
            speed: 语速
            
        Returns:
            Tuple[bool, Optional[str]]: (成功标志, base64 音频数据)
        """
        if not text or not text.strip():
            return False, None
        
        success, audio_bytes = await self.tts.synthesize_to_bytes(
            text,
            voice=voice,
            speed=speed,
        )
        
        if success and audio_bytes:
            return True, base64.b64encode(audio_bytes).decode("utf-8")
        
        return False, None
    
    async def text_to_speech_file(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Tuple[bool, Optional[Path]]:
        """
        将文本转换为语音文件
        
        Args:
            text: 要转换的文本
            voice: 语音音色
            speed: 语速
            
        Returns:
            Tuple[bool, Optional[Path]]: (成功标志, 音频文件路径)
        """
        return await self.tts.synthesize(text, voice=voice, speed=speed)
    
    async def stream_tts_for_text(
        self,
        text_stream: AsyncIterator[str],
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> AsyncIterator[TTSResult]:
        """
        流式处理文本并生成 TTS
        
        监听文本流，检测完整句子并生成语音
        
        Args:
            text_stream: 文本流迭代器
            voice: 语音音色
            speed: 语速
            
        Yields:
            TTSResult: TTS 结果
        """
        buffer = ""
        
        async for chunk in text_stream:
            buffer += chunk
            
            # 提取完整句子
            sentences, buffer = extract_sentences(buffer)
            
            # 为每个完整句子生成 TTS
            for sentence in sentences:
                success, audio_base64 = await self.text_to_speech(
                    sentence,
                    voice=voice,
                    speed=speed,
                )
                yield TTSResult(
                    success=success,
                    sentence=sentence,
                    audio_base64=audio_base64,
                )
        
        # 处理剩余文本
        if buffer.strip():
            success, audio_base64 = await self.text_to_speech(
                buffer,
                voice=voice,
                speed=speed,
            )
            yield TTSResult(
                success=success,
                sentence=buffer,
                audio_base64=audio_base64,
            )
    
    def get_available_voices(self) -> List[str]:
        """获取可用的语音列表"""
        return self.tts.supported_voices
    
    # ==================== ASR 功能 ====================
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        *,
        language: str = "zh",
    ) -> Optional[str]:
        """
        将语音转换为文本
        
        Args:
            audio_data: 音频数据
            language: 语言代码
            
        Returns:
            Optional[str]: 识别的文本
        """
        if not self.asr:
            raise RuntimeError("ASR 提供者未配置")
        
        return await self.asr.transcribe(audio_data, language=language)
    
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
            Optional[str]: 识别的文本
        """
        if not self.asr:
            raise RuntimeError("ASR 提供者未配置")
        
        return await self.asr.transcribe_file(file_path, language=language)
    
    def get_supported_audio_formats(self) -> List[str]:
        """获取支持的音频格式"""
        if not self.asr:
            return []
        return self.asr.supported_formats


class StreamingTTSManager:
    """
    流式 TTS 管理器
    
    管理多个并发 TTS 任务，支持优先级队列
    """
    
    def __init__(
        self,
        tts_provider: TTSProvider,
        max_concurrent: int = 4,
    ):
        self.tts = tts_provider
        self.max_concurrent = max_concurrent
        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._sentence_count = 0
        self._completed_count = 0
    
    async def start(self):
        """启动 TTS 工作器"""
        if self._running:
            return
        
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_concurrent)
        ]
    
    async def stop(self):
        """停止 TTS 工作器"""
        self._running = False
        
        # 等待队列清空
        await self._queue.join()
        
        # 取消工作器
        for worker in self._workers:
            worker.cancel()
        
        self._workers = []
    
    async def _worker(self, worker_id: int):
        """工作器协程"""
        while self._running:
            try:
                priority, counter, sentence = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            try:
                success, audio_bytes = await self.tts.synthesize_to_bytes(sentence)
                
                audio_base64 = None
                if success and audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                
                await self._results.put(TTSResult(
                    success=success,
                    sentence=sentence,
                    audio_base64=audio_base64,
                ))
                
            except Exception as e:
                await self._results.put(TTSResult(
                    success=False,
                    sentence=sentence,
                ))
            finally:
                self._completed_count += 1
                self._queue.task_done()
    
    async def add_text(self, text: str, priority: int = 1):
        """
        添加文本到生成队列
        
        Args:
            text: 要转换的文本
            priority: 优先级（数值越小越优先）
        """
        sentences, _ = extract_sentences(text)
        
        for sentence in sentences:
            self._sentence_count += 1
            await self._queue.put((priority, self._sentence_count, sentence))
    
    async def get_next_result(self, timeout: float = 1.0) -> Optional[TTSResult]:
        """获取下一个完成的 TTS 结果"""
        try:
            return await asyncio.wait_for(
                self._results.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None
    
    def get_pending_count(self) -> int:
        """获取待处理数量"""
        return self._sentence_count - self._completed_count
    
    def reset(self):
        """重置管理器状态"""
        self._sentence_count = 0
        self._completed_count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
