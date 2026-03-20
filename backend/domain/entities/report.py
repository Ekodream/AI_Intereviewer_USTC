"""
报告实体 - 定义面试评估报告的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class ScoreBreakdown:
    """评分明细"""
    professional_knowledge: int = 0     # 专业知识 (30分)
    research_potential: int = 0         # 科研潜力 (30分)
    comprehensive_quality: int = 0      # 综合素质 (20分)
    performance: int = 0                # 临场表现 (10分)
    question_quality: int = 0           # 反问质量 (10分)
    
    @property
    def total(self) -> int:
        """计算总分"""
        return (
            self.professional_knowledge +
            self.research_potential +
            self.comprehensive_quality +
            self.performance +
            self.question_quality
        )
    
    def to_dict(self) -> Dict[str, int]:
        """转换为字典"""
        return {
            "professional_knowledge": self.professional_knowledge,
            "research_potential": self.research_potential,
            "comprehensive_quality": self.comprehensive_quality,
            "performance": self.performance,
            "question_quality": self.question_quality,
            "total": self.total,
        }


@dataclass
class RiskAssessment:
    """风险评估"""
    risk_level: str = "low"  # low, medium, high
    risk_factors: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "concerns": self.concerns,
        }


@dataclass
class Recommendation:
    """建议"""
    decision: str = "pending"  # accept, reject, pending, conditional
    reasons: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    follow_up_questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "decision": self.decision,
            "reasons": self.reasons,
            "improvements": self.improvements,
            "follow_up_questions": self.follow_up_questions,
        }


@dataclass
class Report:
    """
    面试评估报告实体
    
    表示一次面试的完整评估报告
    """
    id: str
    session_id: str
    interview_id: str
    
    # 生成时间
    generated_at: datetime = field(default_factory=datetime.now)
    
    # 报告内容
    title: str = "面试评估报告"
    summary: str = ""                           # 总体评价
    
    # 评分
    scores: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    
    # 各环节评价
    stage_evaluations: Dict[str, str] = field(default_factory=dict)
    
    # 能力分析
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # 风险评估
    risk_assessment: RiskAssessment = field(default_factory=RiskAssessment)
    
    # 建议
    recommendation: Recommendation = field(default_factory=Recommendation)
    
    # 原始 Markdown 内容
    markdown_content: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def format_markdown(self) -> str:
        """
        生成 Markdown 格式的报告
        
        Returns:
            str: Markdown 格式的报告内容
        """
        sections = [
            f"# {self.title}",
            "",
            f"**生成时间**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 总体评价",
            "",
            self.summary,
            "",
            "## 评分明细",
            "",
            f"| 维度 | 分数 | 满分 |",
            f"|------|------|------|",
            f"| 专业知识 | {self.scores.professional_knowledge} | 30 |",
            f"| 科研潜力 | {self.scores.research_potential} | 30 |",
            f"| 综合素质 | {self.scores.comprehensive_quality} | 20 |",
            f"| 临场表现 | {self.scores.performance} | 10 |",
            f"| 反问质量 | {self.scores.question_quality} | 10 |",
            f"| **总分** | **{self.scores.total}** | **100** |",
            "",
        ]
        
        # 各环节评价
        if self.stage_evaluations:
            sections.extend([
                "## 各环节评价",
                "",
            ])
            for stage, evaluation in self.stage_evaluations.items():
                sections.extend([
                    f"### {stage}",
                    "",
                    evaluation,
                    "",
                ])
        
        # 优势与不足
        if self.strengths:
            sections.extend([
                "## 优势",
                "",
                *[f"- {s}" for s in self.strengths],
                "",
            ])
        
        if self.weaknesses:
            sections.extend([
                "## 不足",
                "",
                *[f"- {w}" for w in self.weaknesses],
                "",
            ])
        
        # 风险评估
        sections.extend([
            "## 风险评估",
            "",
            f"**风险等级**: {self.risk_assessment.risk_level}",
            "",
        ])
        
        if self.risk_assessment.risk_factors:
            sections.extend([
                "**风险因素**:",
                *[f"- {r}" for r in self.risk_assessment.risk_factors],
                "",
            ])
        
        # 建议
        sections.extend([
            "## 综合建议",
            "",
            f"**录取建议**: {self._format_decision(self.recommendation.decision)}",
            "",
        ])
        
        if self.recommendation.reasons:
            sections.extend([
                "**理由**:",
                *[f"- {r}" for r in self.recommendation.reasons],
                "",
            ])
        
        if self.recommendation.improvements:
            sections.extend([
                "**改进建议**:",
                *[f"- {i}" for i in self.recommendation.improvements],
                "",
            ])
        
        return "\n".join(sections)
    
    def _format_decision(self, decision: str) -> str:
        """格式化录取决定"""
        mapping = {
            "accept": "建议录取",
            "reject": "不建议录取",
            "pending": "待定",
            "conditional": "有条件录取",
        }
        return mapping.get(decision, decision)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "interview_id": self.interview_id,
            "generated_at": self.generated_at.isoformat(),
            "title": self.title,
            "summary": self.summary,
            "scores": self.scores.to_dict(),
            "stage_evaluations": self.stage_evaluations,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "risk_assessment": self.risk_assessment.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "markdown_content": self.markdown_content,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """从字典创建"""
        report = cls(
            id=data.get("id", ""),
            session_id=data.get("session_id", ""),
            interview_id=data.get("interview_id", ""),
            title=data.get("title", "面试评估报告"),
            summary=data.get("summary", ""),
            stage_evaluations=data.get("stage_evaluations", {}),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            markdown_content=data.get("markdown_content", ""),
            metadata=data.get("metadata", {}),
        )
        
        # 解析评分
        scores_data = data.get("scores", {})
        report.scores = ScoreBreakdown(
            professional_knowledge=scores_data.get("professional_knowledge", 0),
            research_potential=scores_data.get("research_potential", 0),
            comprehensive_quality=scores_data.get("comprehensive_quality", 0),
            performance=scores_data.get("performance", 0),
            question_quality=scores_data.get("question_quality", 0),
        )
        
        # 解析风险评估
        risk_data = data.get("risk_assessment", {})
        report.risk_assessment = RiskAssessment(
            risk_level=risk_data.get("risk_level", "low"),
            risk_factors=risk_data.get("risk_factors", []),
            concerns=risk_data.get("concerns", []),
        )
        
        # 解析建议
        rec_data = data.get("recommendation", {})
        report.recommendation = Recommendation(
            decision=rec_data.get("decision", "pending"),
            reasons=rec_data.get("reasons", []),
            improvements=rec_data.get("improvements", []),
            follow_up_questions=rec_data.get("follow_up_questions", []),
        )
        
        if data.get("generated_at"):
            report.generated_at = datetime.fromisoformat(data["generated_at"])
        
        return report
