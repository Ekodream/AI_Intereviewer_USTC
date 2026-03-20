"""
配置管理 - 使用 Pydantic Settings 实现类型安全的配置
支持环境变量覆盖和 .env 文件加载
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置 - 所有配置项通过环境变量或 .env 文件注入"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ==================== API 密钥配置 ====================
    # StepFun API Keys (用于 TTS 和 ASR) - 支持多 Key 轮询
    STEPFUN_API_KEY_1: str = Field(default="")
    STEPFUN_API_KEY_2: str = Field(default="")
    STEPFUN_API_KEY_3: str = Field(default="")
    STEPFUN_API_KEY_4: str = Field(default="")
    STEPFUN_API_KEY_5: str = Field(default="")
    STEPFUN_API_KEY_6: str = Field(default="")
    STEPFUN_API_KEY_7: str = Field(default="")
    STEPFUN_API_KEY_8: str = Field(default="")
    
    # 阿里云 DashScope API (用于 LLM)
    DASHSCOPE_API_KEY: str = Field(default="")
    
    # ==================== 模型配置 ====================
    # LLM 配置
    LLM_MODEL: str = Field(default="qwen-plus")
    LLM_BASE_URL: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_TIMEOUT: int = Field(default=60, description="LLM 请求超时时间（秒）")
    
    # TTS 配置
    TTS_PROVIDER: str = Field(default="stepfun", description="TTS 提供者: stepfun 或 edge")
    TTS_MODEL: str = Field(default="step-tts-mini")
    TTS_VOICE: str = Field(default="cixingnansheng", description="TTS 音色")
    TTS_TIMEOUT: int = Field(default=30, description="TTS 请求超时时间（秒）")
    
    # ASR 配置
    ASR_MODEL: str = Field(default="step-asr")
    ASR_TIMEOUT: int = Field(default=30, description="ASR 请求超时时间（秒）")
    
    # ==================== 路径配置 ====================
    # 项目根目录（自动检测）
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    # 向量数据库路径
    VECTOR_DB_PATH: Optional[Path] = Field(default=None)
    
    # ==================== 应用配置 ====================
    # 音频配置
    AUDIO_SAMPLE_RATE: int = Field(default=16000)
    
    # 会话配置
    MAX_CONVERSATION_TURNS: int = Field(default=50)
    SESSION_TTL_HOURS: int = Field(default=2, description="会话过期时间（小时）")
    
    # 流式输出配置
    STREAM_DELAY: float = Field(default=0.01, description="流式输出延迟（秒）")
    
    # API Key 轮询配置
    API_KEY_MIN_INTERVAL: float = Field(default=1.5, description="API Key 最小调用间隔（秒）")
    API_KEY_MAX_CONCURRENT: int = Field(default=4, description="API Key 最大并发数")
    
    # ==================== 服务配置 ====================
    # FastAPI 配置
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)
    CORS_ORIGINS: List[str] = Field(default=["*"])
    
    # ==================== 计算属性 ====================
    @property
    def stepfun_api_keys(self) -> List[str]:
        """获取所有非空的 StepFun API Keys"""
        keys = [
            self.STEPFUN_API_KEY_1,
            self.STEPFUN_API_KEY_2,
            self.STEPFUN_API_KEY_3,
            self.STEPFUN_API_KEY_4,
            self.STEPFUN_API_KEY_5,
            self.STEPFUN_API_KEY_6,
            self.STEPFUN_API_KEY_7,
            self.STEPFUN_API_KEY_8,
        ]
        return [k for k in keys if k]
    
    @property
    def data_dir(self) -> Path:
        """数据目录"""
        return self.BASE_DIR / "data"
    
    @property
    def raw_knowledge_dir(self) -> Path:
        """原始知识库目录"""
        return self.data_dir / "raw_knowledge"
    
    @property
    def vector_store_dir(self) -> Path:
        """向量存储目录"""
        return self.data_dir / "vector_store"
    
    @property
    def output_dir(self) -> Path:
        """输出目录"""
        return self.BASE_DIR / "output"
    
    @property
    def reports_dir(self) -> Path:
        """报告输出目录"""
        return self.output_dir / "reports"
    
    @property
    def videos_dir(self) -> Path:
        """视频输出目录"""
        return self.output_dir / "videos"
    
    @property
    def advisor_docs_dir(self) -> Path:
        """导师文档目录"""
        return self.output_dir / "advisor_docs"
    
    @property
    def rooms_dir(self) -> Path:
        """房间数据目录"""
        return self.output_dir / "rooms"
    
    @property
    def rooms_index_file(self) -> Path:
        """房间索引文件"""
        return self.rooms_dir / "rooms.json"
    
    @property
    def temp_dir(self) -> Path:
        """临时文件目录"""
        return self.BASE_DIR / "temp_audio"
    
    @property
    def vector_db_directory(self) -> Path:
        """向量数据库目录"""
        if self.VECTOR_DB_PATH:
            return self.VECTOR_DB_PATH
        return self.BASE_DIR / "vector_db"
    
    def init_directories(self) -> None:
        """创建必要的目录结构"""
        directories = [
            self.data_dir,
            self.raw_knowledge_dir,
            self.vector_store_dir,
            self.output_dir,
            self.reports_dir,
            self.videos_dir,
            self.advisor_docs_dir,
            self.rooms_dir,
            self.temp_dir,
            self.vector_db_directory,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    使用 lru_cache 确保整个应用生命周期内只创建一个 Settings 实例
    """
    return Settings()


# 全局配置实例（便于导入使用）
settings = get_settings()
