"""
领域层实体测试
"""

import pytest
from datetime import datetime


class TestInterviewSession:
    """测试面试会话实体"""
    
    def test_create_session(self):
        """测试创建会话"""
        from backend.domain.entities.interview import InterviewSession
        
        session = InterviewSession(
            session_id="test-123",
            user_id="user-1"
        )
        
        assert session.session_id == "test-123"
        assert session.user_id == "user-1"
        assert session.current_phase == 0
        assert len(session.history) == 0
    
    def test_add_message(self):
        """测试添加消息"""
        from backend.domain.entities.interview import InterviewSession
        
        session = InterviewSession(session_id="test-123")
        session.add_message("user", "你好")
        session.add_message("assistant", "你好！")
        
        assert len(session.history) == 2
        assert session.history[0]["role"] == "user"
        assert session.history[1]["content"] == "你好！"
    
    def test_advance_phase(self):
        """测试推进阶段"""
        from backend.domain.entities.interview import InterviewSession
        
        session = InterviewSession(session_id="test-123")
        assert session.current_phase == 0
        
        session.advance_phase()
        assert session.current_phase == 1
        
        session.set_phase(5)
        assert session.current_phase == 5
    
    def test_get_history_for_llm(self):
        """测试获取 LLM 格式历史"""
        from backend.domain.entities.interview import InterviewSession
        
        session = InterviewSession(session_id="test-123")
        session.add_message("user", "问题1")
        session.add_message("assistant", "回答1")
        session.add_message("user", "问题2")
        
        history = session.get_history_for_llm(limit=2)
        assert len(history) == 2
        assert history[0]["content"] == "回答1"


class TestResumeInfo:
    """测试简历信息值对象"""
    
    def test_create_resume_info(self):
        """测试创建简历信息"""
        from backend.domain.entities.resume import ResumeInfo
        
        resume = ResumeInfo(
            file_name="test.pdf",
            raw_text="姓名：张三",
            analysis="这是一份优秀的简历"
        )
        
        assert resume.file_name == "test.pdf"
        assert "张三" in resume.raw_text
        assert resume.analysis is not None
    
    def test_resume_to_dict(self):
        """测试转换为字典"""
        from backend.domain.entities.resume import ResumeInfo
        
        resume = ResumeInfo(
            file_name="test.pdf",
            raw_text="内容",
            analysis="分析结果"
        )
        
        data = resume.to_dict()
        assert data["file_name"] == "test.pdf"
        assert "raw_text" in data


class TestAdvisorInfo:
    """测试导师信息实体"""
    
    def test_create_advisor_info(self):
        """测试创建导师信息"""
        from backend.domain.entities.advisor import AdvisorInfo
        
        advisor = AdvisorInfo(
            name="何向南",
            school="中国科学技术大学",
            lab="DATA Lab"
        )
        
        assert advisor.name == "何向南"
        assert advisor.school == "中国科学技术大学"
        assert advisor.lab == "DATA Lab"
    
    def test_advisor_key(self):
        """测试生成导师键"""
        from backend.domain.entities.advisor import AdvisorInfo
        
        advisor = AdvisorInfo(
            name="何向南",
            school="中国科学技术大学"
        )
        
        key = advisor.get_key()
        assert "中国科学技术大学" in key
        assert "何向南" in key
