"""
测试配置和通用 fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

# 添加项目根目录到 Python 路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """模拟设置"""
    from backend.config.settings import Settings
    
    settings = MagicMock(spec=Settings)
    settings.STEPFUN_API_KEY = "test_api_key"
    settings.STEPFUN_BASE_URL = "https://api.test.com/v1"
    settings.STEPFUN_CHAT_MODEL = "test-model"
    settings.STEPFUN_EMBEDDING_MODEL = "test-embedding"
    settings.TTS_VOICE = "zh-CN-XiaoxiaoNeural"
    settings.TTS_RATE = "+0%"
    settings.TEMP_AUDIO_DIR = Path("/tmp/test_audio")
    settings.OUTPUT_DIR = Path("/tmp/test_output")
    settings.VECTOR_DB_PATH = Path("/tmp/test_vector_db")
    settings.DATA_DIR = Path("/tmp/test_data")
    return settings


@pytest.fixture
def mock_llm_provider():
    """模拟 LLM 提供者"""
    from backend.domain.interfaces.llm import LLMProvider
    
    provider = AsyncMock(spec=LLMProvider)
    provider.chat.return_value = "这是一个测试响应"
    provider.stream_chat.return_value = async_generator(["这是", "一个", "测试", "响应"])
    return provider


@pytest.fixture
def mock_tts_provider():
    """模拟 TTS 提供者"""
    from backend.domain.interfaces.audio import TTSProvider
    
    provider = AsyncMock(spec=TTSProvider)
    provider.synthesize.return_value = (True, Path("/tmp/test.mp3"))
    provider.synthesize_to_bytes.return_value = (True, b"fake_audio_data")
    return provider


@pytest.fixture
def mock_asr_provider():
    """模拟 ASR 提供者"""
    from backend.domain.interfaces.audio import ASRProvider
    
    provider = AsyncMock(spec=ASRProvider)
    provider.transcribe.return_value = (True, "这是识别出的文本")
    return provider


@pytest.fixture
def mock_session_storage():
    """模拟会话存储"""
    from backend.infrastructure.storage.session_storage import InMemorySessionStorage
    
    return InMemorySessionStorage()


@pytest.fixture
def sample_chat_history():
    """示例聊天历史"""
    return [
        {"role": "user", "content": "你好，我是小明"},
        {"role": "assistant", "content": "你好小明！很高兴认识你。"},
        {"role": "user", "content": "我想了解一下机器学习"},
        {"role": "assistant", "content": "机器学习是人工智能的一个分支..."},
    ]


@pytest.fixture
def sample_resume_text():
    """示例简历文本"""
    return """
    姓名：张三
    学校：中国科学技术大学
    专业：计算机科学与技术
    GPA：3.8/4.0
    
    项目经历：
    1. 基于深度学习的图像识别系统
       - 使用 PyTorch 实现 ResNet 模型
       - 在 ImageNet 数据集上达到 85% 准确率
    
    技能：
    - Python, Java, C++
    - PyTorch, TensorFlow
    - Git, Docker
    """


async def async_generator(items):
    """辅助函数：创建异步生成器"""
    for item in items:
        yield item
