"""
接口模块 - 定义领域服务的抽象接口
"""

from backend.domain.interfaces.llm_provider import LLMProvider
from backend.domain.interfaces.tts_provider import TTSProvider, StreamingTTSProvider
from backend.domain.interfaces.asr_provider import ASRProvider
from backend.domain.interfaces.embedding_provider import EmbeddingProvider
from backend.domain.interfaces.vector_store import VectorStore, SearchResult, Document
from backend.domain.interfaces.storage import (
    Storage,
    SessionStorage,
    FileStorage,
)

__all__ = [
    # LLM
    "LLMProvider",
    # TTS
    "TTSProvider",
    "StreamingTTSProvider",
    # ASR
    "ASRProvider",
    # Embedding
    "EmbeddingProvider",
    # Vector Store
    "VectorStore",
    "SearchResult",
    "Document",
    # Storage
    "Storage",
    "SessionStorage",
    "FileStorage",
]
