"""
实体模块 - 定义核心业务实体
"""

from backend.domain.entities.session import Session, SessionData
from backend.domain.entities.interview import Interview, InterviewStageDetector
from backend.domain.entities.resume import (
    Resume,
    BasicInfo,
    TechnicalSkills,
    WorkExperience,
    Project,
    Assessment,
)
from backend.domain.entities.room import Room, RoomConfig, StudentResult
from backend.domain.entities.report import (
    Report,
    ScoreBreakdown,
    RiskAssessment,
    Recommendation,
)
from backend.domain.entities.advisor import (
    Advisor,
    AdvisorProfile,
    ResearchInfo,
    RecruitmentInfo,
)

__all__ = [
    # Session
    "Session",
    "SessionData",
    # Interview
    "Interview",
    "InterviewStageDetector",
    # Resume
    "Resume",
    "BasicInfo",
    "TechnicalSkills",
    "WorkExperience",
    "Project",
    "Assessment",
    # Room
    "Room",
    "RoomConfig",
    "StudentResult",
    # Report
    "Report",
    "ScoreBreakdown",
    "RiskAssessment",
    "Recommendation",
    # Advisor
    "Advisor",
    "AdvisorProfile",
    "ResearchInfo",
    "RecruitmentInfo",
]
