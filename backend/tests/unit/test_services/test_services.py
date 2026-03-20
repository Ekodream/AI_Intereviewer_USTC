"""
服务层测试
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestAudioService:
    """测试音频服务"""
    
    @pytest.mark.asyncio
    async def test_text_to_speech(self, mock_tts_provider):
        """测试文字转语音"""
        from backend.services.audio_service import AudioService
        
        service = AudioService(
            tts_provider=mock_tts_provider,
            asr_provider=AsyncMock()
        )
        
        success, audio_base64 = await service.text_to_speech("测试文本")
        
        assert success is True
        assert audio_base64 is not None
        mock_tts_provider.synthesize_to_bytes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_speech_to_text(self, mock_asr_provider):
        """测试语音转文字"""
        from backend.services.audio_service import AudioService
        
        service = AudioService(
            tts_provider=AsyncMock(),
            asr_provider=mock_asr_provider
        )
        
        success, text = await service.speech_to_text(b"fake_audio_data")
        
        assert success is True
        assert text == "这是识别出的文本"
        mock_asr_provider.transcribe.assert_called_once()


class TestResumeService:
    """测试简历服务"""
    
    @pytest.mark.asyncio
    async def test_parse_resume(self, mock_llm_provider, sample_resume_text):
        """测试解析简历"""
        from backend.services.resume_service import ResumeService
        
        # Mock PDF 解析
        with patch('backend.services.resume_service.PyPDF2') as mock_pypdf:
            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()]
            mock_reader.pages[0].extract_text.return_value = sample_resume_text
            mock_pypdf.PdfReader.return_value = mock_reader
            
            service = ResumeService(llm_provider=mock_llm_provider)
            
            # 模拟文件
            mock_file = MagicMock()
            mock_file.filename = "test.pdf"
            mock_file.read = AsyncMock(return_value=b"fake_pdf_content")
            
            result = await service.parse(mock_file, "test-session")
            
            assert result["status"] == "ok"
            assert result["file_name"] == "test.pdf"


class TestChatService:
    """测试聊天服务"""
    
    @pytest.mark.asyncio
    async def test_stream_chat(self, mock_llm_provider, mock_session_storage):
        """测试流式聊天"""
        from backend.services.chat_service import ChatService
        
        service = ChatService(
            llm_provider=mock_llm_provider,
            session_storage=mock_session_storage
        )
        
        # 创建会话
        mock_session_storage.create_session("test-session")
        
        chunks = []
        async for chunk in service.stream_chat(
            session_id="test-session",
            user_message="你好",
            system_prompt="你是一个面试官"
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        # 检查最后一个 chunk 是 done
        assert chunks[-1]["type"] == "done"


class TestRoomService:
    """测试房间服务"""
    
    def test_create_room(self, mock_settings):
        """测试创建房间"""
        from backend.services.room_service import RoomService
        
        with patch('backend.services.room_service.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.mkdir = MagicMock()
            
            service = RoomService(output_dir=mock_settings.OUTPUT_DIR)
            
            room = service.create_room(
                teacher_name="张老师",
                config={"enable_tts": True}
            )
            
            assert room is not None
            assert room["teacher_name"] == "张老师"
            assert len(room["room_id"]) == 6
    
    def test_join_room(self, mock_settings):
        """测试加入房间"""
        from backend.services.room_service import RoomService
        
        service = RoomService(output_dir=mock_settings.OUTPUT_DIR)
        
        # 先创建房间
        with patch.object(service, '_load_rooms', return_value={}):
            with patch.object(service, '_save_rooms'):
                room = service.create_room("张老师", {})
                room_id = room["room_id"]
        
        # 尝试加入
        with patch.object(service, '_load_rooms', return_value={room_id: room}):
            result = service.join_room(room_id)
            assert result is not None
            assert result["room_id"] == room_id
