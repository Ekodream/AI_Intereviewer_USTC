"""
简历服务 - 处理简历上传、解析和分析相关业务逻辑
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import pdfplumber
from openai import OpenAI

from backend.domain.interfaces.storage import FileStorage
from backend.domain.interfaces.llm_provider import LLMProvider


RESUME_ANALYSIS_PROMPT = """你是一位技术面试导师，请快速分析这份简历并提取关键信息。

请严格以 JSON 格式返回（不要任何额外文字）：
{
  "basic_info": {
    "name": "姓名",
    "contact": "联系方式",
    "years_of_experience": 工作年限（数字）
  },
  "technical_skills": {
    "programming_languages": ["语言列表"],
    "frameworks": ["框架列表"],
    "databases": ["数据库列表"],
    "tools": ["工具列表"]
  },
  "work_experience": [
    {"company": "公司", "position": "职位", "duration": "时间", "responsibilities": ["职责"]}
  ],
  "projects": [
    {"name": "项目名", "technologies": ["技术"], "highlights": ["亮点"], "contribution": "贡献"}
  ],
  "assessment": {
    "technical_depth_score": 1-10 的整数，
    "technical_breadth_score": 1-10 的整数，
    "risk_points": ["风险点"]
  }
}

评估标准：
- 技术深度：项目复杂度、技术难点
- 技术广度：技能多样性
- 风险点：频繁跳槽、技能不匹配等"""


@dataclass
class ResumeAnalysis:
    """简历分析结果"""
    basic_info: Dict[str, Any] = field(default_factory=dict)
    technical_skills: Dict[str, Any] = field(default_factory=dict)
    work_experience: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    assessment: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "basic_info": self.basic_info,
            "technical_skills": self.technical_skills,
            "work_experience": self.work_experience,
            "projects": self.projects,
            "assessment": self.assessment,
            "raw_text": self.raw_text,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeAnalysis":
        return cls(
            basic_info=data.get("basic_info", {}),
            technical_skills=data.get("technical_skills", {}),
            work_experience=data.get("work_experience", []),
            projects=data.get("projects", []),
            assessment=data.get("assessment", {}),
            raw_text=data.get("raw_text", ""),
        )


class ResumeService:
    """
    简历服务
    
    处理简历上传、解析、分析等业务逻辑
    """
    
    def __init__(
        self,
        file_storage: FileStorage,
        api_key: str,
        llm_model: str = "qwen-plus",
    ):
        self.file_storage = file_storage
        self.api_key = api_key
        self.llm_model = llm_model
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """从 PDF 文件提取文本"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise Exception(f"PDF 解析失败：{str(e)}")
        
        return text.strip()
    
    async def save_resume(
        self,
        content: bytes,
        filename: str,
        session_id: str,
    ) -> str:
        """保存简历文件"""
        return await self.file_storage.save(
            content,
            filename,
            directory=f"resumes/{session_id}",
        )
    
    async def parse_resume(self, file_path: Path) -> ResumeAnalysis:
        """
        解析并分析简历
        
        Args:
            file_path: 简历文件路径
            
        Returns:
            ResumeAnalysis: 简历分析结果
        """
        # 提取文本
        text = await asyncio.to_thread(self.extract_text_from_pdf, file_path)
        
        if not text or len(text) < 50:
            raise Exception("简历内容过少，可能 PDF 解析失败或文件损坏")
        
        # 使用 LLM 分析
        analysis_dict = await self._analyze_with_llm(text)
        analysis_dict["raw_text"] = text
        
        return ResumeAnalysis.from_dict(analysis_dict)
    
    async def _analyze_with_llm(self, resume_text: str) -> Dict[str, Any]:
        """使用 LLM 分析简历内容"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一位资深技术面试导师，擅长简历分析和人才评估。请严格以 JSON 格式返回分析结果。"
            },
            {
                "role": "user",
                "content": f"{RESUME_ANALYSIS_PROMPT}\n\n以下是简历内容：\n{'='*50}\n{resume_text}\n{'='*50}"
            }
        ]
        
        def _call_llm():
            completion = self._client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                stream=False,
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        
        try:
            response_text = await asyncio.to_thread(_call_llm)
            
            # 处理可能的 markdown 代码块
            if response_text.startswith("```"):
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                elif response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            # 验证必要字段
            for field in ["basic_info", "technical_skills", "assessment"]:
                if field not in result:
                    result[field] = {}
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"LLM 返回格式错误，无法解析为 JSON: {e}")
        except Exception as e:
            raise Exception(f"简历分析失败：{e}")
    
    def format_for_prompt(self, analysis: ResumeAnalysis) -> str:
        """将简历分析结果格式化为 prompt 格式"""
        basic = analysis.basic_info
        skills = analysis.technical_skills
        work = analysis.work_experience
        projects = analysis.projects
        assess = analysis.assessment
        
        lines = []
        
        # 基本信息
        lines.append("【候选人基本信息】")
        if basic.get("name"):
            lines.append(f"姓名：{basic['name']}")
        if basic.get("contact"):
            lines.append(f"联系方式：{basic['contact']}")
        if basic.get("years_of_experience", 0) > 0:
            lines.append(f"工作年限：{basic['years_of_experience']}年")
        lines.append("")
        
        # 技术栈
        lines.append("【技术栈】")
        if skills.get("programming_languages"):
            lines.append(f"编程语言：{', '.join(skills['programming_languages'])}")
        if skills.get("frameworks"):
            lines.append(f"框架：{', '.join(skills['frameworks'])}")
        if skills.get("databases"):
            lines.append(f"数据库：{', '.join(skills['databases'])}")
        if skills.get("tools"):
            lines.append(f"工具：{', '.join(skills['tools'])}")
        lines.append("")
        
        # 工作经历
        if work:
            lines.append("【工作经历】")
            for idx, job in enumerate(work[:3], 1):
                company = job.get("company", "未知公司")
                position = job.get("position", "未知职位")
                duration = job.get("duration", "")
                lines.append(f"{idx}. {company} - {position} {duration}")
            lines.append("")
        
        # 项目经验
        if projects:
            lines.append("【重点项目】")
            for idx, proj in enumerate(projects[:3], 1):
                name = proj.get("name", "未知项目")
                tech = ", ".join(proj.get("technologies", []))
                lines.append(f"{idx}. {name}（技术栈：{tech}）")
            lines.append("")
        
        # 能力评估
        lines.append("【能力评估】")
        depth = assess.get("technical_depth_score", 0)
        breadth = assess.get("technical_breadth_score", 0)
        lines.append(f"技术深度评分：{depth}/10")
        lines.append(f"技术广度评分：{breadth}/10")
        if assess.get("risk_points"):
            lines.append(f"风险提示：{', '.join(assess['risk_points'])}")
        
        return "\n".join(lines)
