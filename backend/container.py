"""
依赖注入容器 - 管理应用依赖的创建和生命周期
"""

from typing import Optional
from functools import lru_cache
from pathlib import Path

from backend.config.settings import get_settings
from backend.domain.interfaces.llm_provider import LLMProvider
from backend.domain.interfaces.tts_provider import TTSProvider
from backend.domain.interfaces.asr_provider import ASRProvider
from backend.infrastructure.llm.llm_factory import LLMFactory
from backend.infrastructure.tts.edge_tts_provider import EdgeTTSProvider
from backend.infrastructure.asr.stepfun_asr import StepFunASRProvider
from backend.infrastructure.storage.session_storage import (
    InMemorySessionStorage,
    LocalFileStorage,
    SessionManager,
)
from backend.services.chat_service import ChatService
from backend.services.interview_service import InterviewService
from backend.services.audio_service import AudioService
from backend.services.resume_service import ResumeService
from backend.services.advisor_service import AdvisorService
from backend.services.room_service import RoomService
from backend.services.report_service import ReportService


class Container:
    """
    依赖注入容器
    
    集中管理应用中所有服务的创建和依赖关系
    """
    
    _instance: Optional["Container"] = None
    
    def __init__(self):
        """初始化容器"""
        self._settings = get_settings()
        
        # 基础设施层
        self._llm_provider: Optional[LLMProvider] = None
        self._tts_provider: Optional[TTSProvider] = None
        self._asr_provider: Optional[ASRProvider] = None
        self._session_storage: Optional[InMemorySessionStorage] = None
        self._file_storage: Optional[LocalFileStorage] = None
        self._session_manager: Optional[SessionManager] = None
        
        # 服务层
        self._chat_service: Optional[ChatService] = None
        self._interview_service: Optional[InterviewService] = None
        self._audio_service: Optional[AudioService] = None
        self._resume_service: Optional[ResumeService] = None
        self._advisor_service: Optional[AdvisorService] = None
        self._room_service: Optional[RoomService] = None
        self._report_service: Optional[ReportService] = None
    
    @classmethod
    def instance(cls) -> "Container":
        """获取容器单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """重置容器(主要用于测试)"""
        cls._instance = None
    
    # ==================== 基础设施层 ====================
    
    def get_llm_provider(self) -> LLMProvider:
        """获取 LLM 提供者"""
        if self._llm_provider is None:
            self._llm_provider = LLMFactory.get_default()
        return self._llm_provider
    
    def get_tts_provider(self) -> TTSProvider:
        """获取 TTS 提供者"""
        if self._tts_provider is None:
            self._tts_provider = EdgeTTSProvider(
                output_dir=self._settings.temp_dir,
            )
        return self._tts_provider
    
    def get_asr_provider(self) -> Optional[ASRProvider]:
        """获取 ASR 提供者"""
        if self._asr_provider is None:
            api_key = self._settings.STEPFUN_API_KEY
            if api_key:
                self._asr_provider = StepFunASRProvider(api_key=api_key)
        return self._asr_provider
    
    def get_session_storage(self) -> InMemorySessionStorage:
        """获取会话存储"""
        if self._session_storage is None:
            self._session_storage = InMemorySessionStorage()
        return self._session_storage
    
    def get_file_storage(self) -> LocalFileStorage:
        """获取文件存储"""
        if self._file_storage is None:
            self._file_storage = LocalFileStorage(
                base_dir=self._settings.output_dir,
            )
        return self._file_storage
    
    def get_session_manager(self) -> SessionManager:
        """获取会话管理器"""
        if self._session_manager is None:
            self._session_manager = SessionManager(
                storage=self.get_session_storage(),
            )
        return self._session_manager
    
    # ==================== 服务层 ====================
    
    def get_chat_service(self) -> ChatService:
        """获取对话服务"""
        if self._chat_service is None:
            self._chat_service = ChatService(
                llm_provider=self.get_llm_provider(),
            )
        return self._chat_service
    
    def get_interview_service(self) -> InterviewService:
        """获取面试服务"""
        if self._interview_service is None:
            self._interview_service = InterviewService()
        return self._interview_service
    
    def get_audio_service(self) -> AudioService:
        """获取音频服务"""
        if self._audio_service is None:
            self._audio_service = AudioService(
                tts_provider=self.get_tts_provider(),
                asr_provider=self.get_asr_provider(),
            )
        return self._audio_service
    
    def get_resume_service(self) -> ResumeService:
        """获取简历服务"""
        if self._resume_service is None:
            self._resume_service = ResumeService(
                file_storage=self.get_file_storage(),
                api_key=self._settings.DASHSCOPE_API_KEY,
            )
        return self._resume_service
    
    def get_advisor_service(self) -> AdvisorService:
        """获取导师服务"""
        if self._advisor_service is None:
            self._advisor_service = AdvisorService(
                api_keys=self._settings.dashscope_api_keys,
            )
        return self._advisor_service
    
    def get_room_service(self) -> RoomService:
        """获取房间服务"""
        if self._room_service is None:
            self._room_service = RoomService(
                rooms_dir=self._settings.rooms_dir,
            )
        return self._room_service
    
    def get_report_service(self) -> ReportService:
        """获取报告服务"""
        if self._report_service is None:
            self._report_service = ReportService(
                api_key=self._settings.DASHSCOPE_API_KEY,
            )
        return self._report_service


# 便捷函数
@lru_cache()
def get_container() -> Container:
    """获取容器单例"""
    return Container.instance()


def get_llm_provider() -> LLMProvider:
    """获取 LLM 提供者"""
    return get_container().get_llm_provider()


def get_chat_service() -> ChatService:
    """获取对话服务"""
    return get_container().get_chat_service()


def get_interview_service() -> InterviewService:
    """获取面试服务"""
    return get_container().get_interview_service()
