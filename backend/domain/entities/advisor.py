"""
导师实体 - 定义导师信息的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class AdvisorProfile:
    """导师基本信息"""
    name: str = ""
    school: str = ""
    department: str = ""
    title: str = ""  # 职称
    email: str = ""
    homepage: str = ""
    
    # 别名（用于搜索匹配）
    name_aliases: List[str] = field(default_factory=list)
    school_aliases: List[str] = field(default_factory=list)


@dataclass
class ResearchInfo:
    """研究信息"""
    research_directions: List[str] = field(default_factory=list)
    research_keywords: List[str] = field(default_factory=list)
    recent_papers: List[Dict[str, str]] = field(default_factory=list)
    projects: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class RecruitmentInfo:
    """招生信息"""
    is_recruiting: bool = True
    preferred_backgrounds: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    research_style: str = ""
    training_approach: str = ""
    student_feedback: List[str] = field(default_factory=list)


@dataclass
class Advisor:
    """
    导师实体
    
    表示一位导师的完整信息
    """
    id: str
    
    # 基本信息
    profile: AdvisorProfile = field(default_factory=AdvisorProfile)
    
    # 研究信息
    research: ResearchInfo = field(default_factory=ResearchInfo)
    
    # 招生信息
    recruitment: RecruitmentInfo = field(default_factory=RecruitmentInfo)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 搜索来源
    sources: List[str] = field(default_factory=list)
    reference_links: List[str] = field(default_factory=list)
    
    # 验证状态
    is_verified: bool = False
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format_for_prompt(self) -> str:
        """
        格式化导师信息用于系统提示词
        
        Returns:
            str: Markdown 格式的导师信息
        """
        sections = []
        
        # 基本信息
        sections.append(f"## 导师信息")
        sections.append(f"- 姓名: {self.profile.name}")
        if self.profile.school:
            sections.append(f"- 学校: {self.profile.school}")
        if self.profile.department:
            sections.append(f"- 院系: {self.profile.department}")
        if self.profile.title:
            sections.append(f"- 职称: {self.profile.title}")
        
        # 研究方向
        if self.research.research_directions:
            sections.append(f"\n## 研究方向")
            for direction in self.research.research_directions:
                sections.append(f"- {direction}")
        
        # 招生偏好
        if self.recruitment.preferred_backgrounds:
            sections.append(f"\n## 招生偏好")
            sections.append(f"- 偏好背景: {', '.join(self.recruitment.preferred_backgrounds)}")
        if self.recruitment.required_skills:
            sections.append(f"- 要求技能: {', '.join(self.recruitment.required_skills)}")
        
        # 培养风格
        if self.recruitment.research_style:
            sections.append(f"\n## 培养风格")
            sections.append(self.recruitment.research_style)
        
        return "\n".join(sections)
    
    def matches_query(self, name: str, school: str = "") -> bool:
        """
        检查是否匹配查询条件
        
        Args:
            name: 导师姓名
            school: 学校名称（可选）
            
        Returns:
            bool: 是否匹配
        """
        # 检查姓名匹配
        name_matches = (
            name.lower() in self.profile.name.lower() or
            self.profile.name.lower() in name.lower() or
            any(name.lower() in alias.lower() for alias in self.profile.name_aliases)
        )
        
        if not name_matches:
            return False
        
        # 如果没有指定学校，只要姓名匹配就行
        if not school:
            return True
        
        # 检查学校匹配
        school_matches = (
            school.lower() in self.profile.school.lower() or
            self.profile.school.lower() in school.lower() or
            any(school.lower() in alias.lower() for alias in self.profile.school_aliases)
        )
        
        return school_matches
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "profile": {
                "name": self.profile.name,
                "school": self.profile.school,
                "department": self.profile.department,
                "title": self.profile.title,
                "email": self.profile.email,
                "homepage": self.profile.homepage,
                "name_aliases": self.profile.name_aliases,
                "school_aliases": self.profile.school_aliases,
            },
            "research": {
                "research_directions": self.research.research_directions,
                "research_keywords": self.research.research_keywords,
                "recent_papers": self.research.recent_papers,
                "projects": self.research.projects,
            },
            "recruitment": {
                "is_recruiting": self.recruitment.is_recruiting,
                "preferred_backgrounds": self.recruitment.preferred_backgrounds,
                "required_skills": self.recruitment.required_skills,
                "research_style": self.recruitment.research_style,
                "training_approach": self.recruitment.training_approach,
                "student_feedback": self.recruitment.student_feedback,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sources": self.sources,
            "reference_links": self.reference_links,
            "is_verified": self.is_verified,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Advisor":
        """从字典创建"""
        profile_data = data.get("profile", {})
        research_data = data.get("research", {})
        recruitment_data = data.get("recruitment", {})
        
        advisor = cls(
            id=data.get("id", ""),
            sources=data.get("sources", []),
            reference_links=data.get("reference_links", []),
            is_verified=data.get("is_verified", False),
            metadata=data.get("metadata", {}),
        )
        
        # 解析基本信息
        advisor.profile = AdvisorProfile(
            name=profile_data.get("name", ""),
            school=profile_data.get("school", ""),
            department=profile_data.get("department", ""),
            title=profile_data.get("title", ""),
            email=profile_data.get("email", ""),
            homepage=profile_data.get("homepage", ""),
            name_aliases=profile_data.get("name_aliases", []),
            school_aliases=profile_data.get("school_aliases", []),
        )
        
        # 解析研究信息
        advisor.research = ResearchInfo(
            research_directions=research_data.get("research_directions", []),
            research_keywords=research_data.get("research_keywords", []),
            recent_papers=research_data.get("recent_papers", []),
            projects=research_data.get("projects", []),
        )
        
        # 解析招生信息
        advisor.recruitment = RecruitmentInfo(
            is_recruiting=recruitment_data.get("is_recruiting", True),
            preferred_backgrounds=recruitment_data.get("preferred_backgrounds", []),
            required_skills=recruitment_data.get("required_skills", []),
            research_style=recruitment_data.get("research_style", ""),
            training_approach=recruitment_data.get("training_approach", ""),
            student_feedback=recruitment_data.get("student_feedback", []),
        )
        
        if data.get("created_at"):
            advisor.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            advisor.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return advisor
