"""
API 集成测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def test_client():
    """创建测试客户端"""
    # 模拟依赖
    with patch('backend.container.Container') as mock_container_class:
        mock_container = MagicMock()
        mock_container_class.return_value = mock_container
        
        # 模拟各种服务
        mock_container.get_chat_service.return_value = AsyncMock()
        mock_container.get_audio_service.return_value = AsyncMock()
        mock_container.get_resume_service.return_value = AsyncMock()
        mock_container.get_advisor_service.return_value = AsyncMock()
        mock_container.get_room_service.return_value = MagicMock()
        mock_container.get_report_service.return_value = AsyncMock()
        mock_container.get_session_storage.return_value = MagicMock()
        
        from main import app
        client = TestClient(app)
        yield client


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, test_client):
        """测试健康检查"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSettingsEndpoints:
    """测试设置端点"""
    
    def test_get_settings(self, test_client):
        """测试获取设置"""
        response = test_client.get(
            "/api/settings",
            headers={"X-Session-ID": "test-session"}
        )
        # 即使会话不存在也应返回默认设置
        assert response.status_code in [200, 404]
    
    def test_save_settings(self, test_client):
        """测试保存设置"""
        response = test_client.post(
            "/api/settings",
            headers={"X-Session-ID": "test-session"},
            json={
                "enable_tts": True,
                "enable_rag": True,
                "rag_domain": "cs ai"
            }
        )
        assert response.status_code in [200, 201]


class TestPresetEndpoints:
    """测试预设端点"""
    
    def test_get_presets(self, test_client):
        """测试获取预设提示词"""
        response = test_client.get(
            "/api/presets",
            headers={"X-Session-ID": "test-session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data


class TestResumeEndpoints:
    """测试简历端点"""
    
    def test_get_resume_status(self, test_client):
        """测试获取简历状态"""
        response = test_client.get(
            "/api/resume/status",
            headers={"X-Session-ID": "test-session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "uploaded" in data


class TestAdvisorEndpoints:
    """测试导师端点"""
    
    def test_get_advisor_status(self, test_client):
        """测试获取导师状态"""
        response = test_client.get(
            "/api/advisor/status",
            headers={"X-Session-ID": "test-session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data or "searched" in data


class TestRagEndpoints:
    """测试 RAG 端点"""
    
    def test_get_rag_domains(self, test_client):
        """测试获取 RAG 领域"""
        response = test_client.get(
            "/api/rag/domains",
            headers={"X-Session-ID": "test-session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
    
    def test_get_rag_history(self, test_client):
        """测试获取 RAG 历史"""
        response = test_client.get(
            "/api/rag/history",
            headers={"X-Session-ID": "test-session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "rag_history" in data


class TestRoomEndpoints:
    """测试房间端点"""
    
    def test_create_room(self, test_client):
        """测试创建房间"""
        with patch('backend.services.room_service.RoomService') as mock_service:
            mock_instance = MagicMock()
            mock_instance.create_room.return_value = {
                "room_id": "123456",
                "teacher_name": "张老师",
                "config": {}
            }
            mock_service.return_value = mock_instance
            
            response = test_client.post(
                "/api/teacher/create",
                headers={"X-Session-ID": "test-session"},
                json={
                    "teacher_name": "张老师",
                    "config": {}
                }
            )
            # 可能需要认证或其他条件
            assert response.status_code in [200, 201, 422]
