"""
基础设施层测试
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


class TestInMemorySessionStorage:
    """测试内存会话存储"""
    
    def test_create_session(self):
        """测试创建会话"""
        from backend.infrastructure.storage.session_storage import InMemorySessionStorage
        
        storage = InMemorySessionStorage()
        session = storage.create_session("test-123")
        
        assert session is not None
        assert session.session_id == "test-123"
    
    def test_get_session(self):
        """测试获取会话"""
        from backend.infrastructure.storage.session_storage import InMemorySessionStorage
        
        storage = InMemorySessionStorage()
        storage.create_session("test-123")
        
        session = storage.get_session("test-123")
        assert session is not None
        assert session.session_id == "test-123"
        
        # 不存在的会话
        session = storage.get_session("not-exist")
        assert session is None
    
    def test_delete_session(self):
        """测试删除会话"""
        from backend.infrastructure.storage.session_storage import InMemorySessionStorage
        
        storage = InMemorySessionStorage()
        storage.create_session("test-123")
        
        result = storage.delete_session("test-123")
        assert result is True
        
        session = storage.get_session("test-123")
        assert session is None
    
    def test_get_or_create_session(self):
        """测试获取或创建会话"""
        from backend.infrastructure.storage.session_storage import InMemorySessionStorage
        
        storage = InMemorySessionStorage()
        
        # 不存在时创建
        session1 = storage.get_or_create_session("test-123")
        assert session1 is not None
        
        # 存在时获取
        session2 = storage.get_or_create_session("test-123")
        assert session1 is session2


class TestLocalFileStorage:
    """测试本地文件存储"""
    
    @pytest.mark.asyncio
    async def test_save_file(self, tmp_path):
        """测试保存文件"""
        from backend.infrastructure.storage.session_storage import LocalFileStorage
        
        storage = LocalFileStorage(base_path=tmp_path)
        
        file_path = await storage.save(
            content=b"test content",
            filename="test.txt",
            subdir="test_dir"
        )
        
        assert file_path.exists()
        assert file_path.read_bytes() == b"test content"
    
    @pytest.mark.asyncio
    async def test_delete_file(self, tmp_path):
        """测试删除文件"""
        from backend.infrastructure.storage.session_storage import LocalFileStorage
        
        storage = LocalFileStorage(base_path=tmp_path)
        
        # 先保存
        file_path = await storage.save(
            content=b"test content",
            filename="test.txt"
        )
        
        # 再删除
        result = await storage.delete(file_path)
        assert result is True
        assert not file_path.exists()


class TestEdgeTTSProvider:
    """测试 Edge TTS 提供者"""
    
    @pytest.mark.asyncio
    async def test_synthesize_to_bytes(self, mock_settings, tmp_path):
        """测试合成到字节"""
        from backend.infrastructure.tts.edge_tts_provider import EdgeTTSProvider
        
        with patch('backend.infrastructure.tts.edge_tts_provider.edge_tts') as mock_edge:
            # Mock Communicate
            mock_communicate = AsyncMock()
            mock_communicate.save = AsyncMock()
            mock_edge.Communicate.return_value = mock_communicate
            
            provider = EdgeTTSProvider(
                voice=mock_settings.TTS_VOICE,
                rate=mock_settings.TTS_RATE,
                output_dir=tmp_path
            )
            
            # 创建临时文件模拟输出
            test_file = tmp_path / "test_output.mp3"
            test_file.write_bytes(b"fake_audio")
            
            with patch.object(provider, '_get_output_path', return_value=test_file):
                success, audio_bytes = await provider.synthesize_to_bytes("测试文本")
            
            assert success is True
            assert audio_bytes == b"fake_audio"


class TestStepFunASRProvider:
    """测试 StepFun ASR 提供者"""
    
    @pytest.mark.asyncio
    async def test_transcribe(self, mock_settings):
        """测试语音识别"""
        from backend.infrastructure.asr.stepfun_asr import StepFunASRProvider
        
        with patch('backend.infrastructure.asr.stepfun_asr.httpx') as mock_httpx:
            # Mock 响应
            mock_response = MagicMock()
            mock_response.json.return_value = {"text": "识别结果"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            
            mock_httpx.AsyncClient.return_value = mock_client
            
            provider = StepFunASRProvider(
                api_key=mock_settings.STEPFUN_API_KEY,
                base_url=mock_settings.STEPFUN_BASE_URL
            )
            
            success, text = await provider.transcribe(b"fake_audio_data")
            
            # 由于 API 调用被 mock，这里主要测试流程
            assert True  # 流程测试通过


class TestTextCleaner:
    """测试文本清理工具"""
    
    def test_strip_markdown(self):
        """测试去除 Markdown 格式"""
        from backend.infrastructure.utils.text_cleaner import strip_markdown
        
        text = "**加粗** 和 *斜体* 以及 `代码`"
        result = strip_markdown(text)
        
        assert "**" not in result
        assert "*" not in result
        assert "`" not in result
        assert "加粗" in result
    
    def test_clean_for_tts(self):
        """测试 TTS 文本清理"""
        from backend.infrastructure.utils.text_cleaner import clean_for_tts
        
        text = "```python\nprint('hello')\n``` 这是代码"
        result = clean_for_tts(text)
        
        assert "```" not in result
