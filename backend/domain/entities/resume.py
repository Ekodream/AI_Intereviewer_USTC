"""
简历实体 - 定义简历的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class BasicInfo:
    """基本信息"""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    years_of_experience: int = 0
    education: str = ""
    

@dataclass
class TechnicalSkills:
    """技术技能"""
    programming_languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    other: List[str] = field(default_factory=list)


@dataclass
class WorkExperience:
    """工作经历"""
    company: str = ""
    position: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)


@dataclass
class Project:
    """项目经历"""
    name: str = ""
    description: str = ""
    technologies: List[str] = field(default_factory=list)
    role: str = ""
    highlights: List[str] = field(default_factory=list)
    contribution: str = ""


@dataclass
class Assessment:
    """评估结果"""
    technical_depth_score: int = 0      # 技术深度评分 (0-100)
    technical_breadth_score: int = 0    # 技术广度评分 (0-100)
    experience_relevance: int = 0       # 经验相关性 (0-100)
    risk_points: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    interview_focus: List[str] = field(default_factory=list)  # 建议面试重点


@dataclass
class Resume:
    """
    简历实体
    
    表示解析后的结构化简历数据
    """
    id: str
    session_id: str
    
    # 原始数据
    raw_text: str = ""
    file_path: str = ""
    file_name: str = ""
    
    # 解析时间
    parsed_at: datetime = field(default_factory=datetime.now)
    
    # 结构化数据
    basic_info: BasicInfo = field(default_factory=BasicInfo)
    technical_skills: TechnicalSkills = field(default_factory=TechnicalSkills)
    work_experience: List[WorkExperience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    education_details: List[Dict[str, str]] = field(default_factory=list)
    
    # 评估结果
    assessment: Assessment = field(default_factory=Assessment)
    
    # 额外信息
    publications: List[str] = field(default_factory=list)
    awards: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    
    def format_for_prompt(self) -> str:
        """
        格式化简历信息用于系统提示词
        
        Returns:
            str: Markdown 格式的简历摘要
        """
        sections = []
        
        # 基本信息
        if self.basic_info.name:
            sections.append(f"## 候选人信息\n- 姓名: {self.basic_info.name}")
            if self.basic_info.education:
                sections.append(f"- 学历: {self.basic_info.education}")
            if self.basic_info.years_of_experience:
                sections.append(f"- 工作年限: {self.basic_info.years_of_experience}年")
        
        # 技术技能
        skills_parts = []
        if self.technical_skills.programming_languages:
            skills_parts.append(f"编程语言: {', '.join(self.technical_skills.programming_languages)}")
        if self.technical_skills.frameworks:
            skills_parts.append(f"框架: {', '.join(self.technical_skills.frameworks)}")
        if self.technical_skills.databases:
            skills_parts.append(f"数据库: {', '.join(self.technical_skills.databases)}")
        if skills_parts:
            sections.append(f"\n## 技术技能\n" + "\n".join(f"- {s}" for s in skills_parts))
        
        # 项目经历
        if self.projects:
            project_parts = ["\n## 项目经历"]
            for i, proj in enumerate(self.projects[:3], 1):  # 最多显示3个
                project_parts.append(f"\n### {i}. {proj.name}")
                if proj.description:
                    project_parts.append(f"- 描述: {proj.description[:200]}...")
                if proj.technologies:
                    project_parts.append(f"- 技术栈: {', '.join(proj.technologies)}")
                if proj.highlights:
                    project_parts.append(f"- 亮点: {'; '.join(proj.highlights[:3])}")
            sections.append("\n".join(project_parts))
        
        # 评估建议
        if self.assessment.interview_focus:
            sections.append(f"\n## 面试重点建议\n" + 
                          "\n".join(f"- {f}" for f in self.assessment.interview_focus))
        
        if self.assessment.risk_points:
            sections.append(f"\n## 需要关注的点\n" + 
                          "\n".join(f"- {r}" for r in self.assessment.risk_points))
        
        return "\n".join(sections) if sections else "简历信息暂无"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "raw_text": self.raw_text,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "parsed_at": self.parsed_at.isoformat(),
            "basic_info": {
                "name": self.basic_info.name,
                "email": self.basic_info.email,
                "phone": self.basic_info.phone,
                "location": self.basic_info.location,
                "years_of_experience": self.basic_info.years_of_experience,
                "education": self.basic_info.education,
            },
            "technical_skills": {
                "programming_languages": self.technical_skills.programming_languages,
                "frameworks": self.technical_skills.frameworks,
                "databases": self.technical_skills.databases,
                "tools": self.technical_skills.tools,
                "other": self.technical_skills.other,
            },
            "work_experience": [
                {
                    "company": w.company,
                    "position": w.position,
                    "start_date": w.start_date,
                    "end_date": w.end_date,
                    "responsibilities": w.responsibilities,
                    "achievements": w.achievements,
                }
                for w in self.work_experience
            ],
            "projects": [
                {
                    "name": p.name,
                    "description": p.description,
                    "technologies": p.technologies,
                    "role": p.role,
                    "highlights": p.highlights,
                    "contribution": p.contribution,
                }
                for p in self.projects
            ],
            "assessment": {
                "technical_depth_score": self.assessment.technical_depth_score,
                "technical_breadth_score": self.assessment.technical_breadth_score,
                "experience_relevance": self.assessment.experience_relevance,
                "risk_points": self.assessment.risk_points,
                "strengths": self.assessment.strengths,
                "weaknesses": self.assessment.weaknesses,
                "interview_focus": self.assessment.interview_focus,
            },
            "publications": self.publications,
            "awards": self.awards,
            "certifications": self.certifications,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Resume":
        """从字典创建"""
        resume = cls(
            id=data.get("id", ""),
            session_id=data.get("session_id", ""),
            raw_text=data.get("raw_text", ""),
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
        )
        
        # 解析基本信息
        basic = data.get("basic_info", {})
        resume.basic_info = BasicInfo(
            name=basic.get("name", ""),
            email=basic.get("email", ""),
            phone=basic.get("phone", ""),
            location=basic.get("location", ""),
            years_of_experience=basic.get("years_of_experience", 0),
            education=basic.get("education", ""),
        )
        
        # 解析技术技能
        skills = data.get("technical_skills", {})
        resume.technical_skills = TechnicalSkills(
            programming_languages=skills.get("programming_languages", []),
            frameworks=skills.get("frameworks", []),
            databases=skills.get("databases", []),
            tools=skills.get("tools", []),
            other=skills.get("other", []),
        )
        
        # 解析评估结果
        assessment = data.get("assessment", {})
        resume.assessment = Assessment(
            technical_depth_score=assessment.get("technical_depth_score", 0),
            technical_breadth_score=assessment.get("technical_breadth_score", 0),
            experience_relevance=assessment.get("experience_relevance", 0),
            risk_points=assessment.get("risk_points", []),
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
            interview_focus=assessment.get("interview_focus", []),
        )
        
        return resume
