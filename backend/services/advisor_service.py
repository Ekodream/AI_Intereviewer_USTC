"""
导师服务 - 处理导师信息搜索和管理相关业务逻辑
"""

import asyncio
import re
from urllib.parse import quote_plus
from typing import Dict, Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class AdvisorInfo:
    """导师信息"""
    school: str = ""
    lab: str = ""
    name: str = ""
    research_direction: str = ""
    recruitment_preference: str = ""
    academic_style: str = ""
    training_method: str = ""
    students_background: str = ""
    recent_papers: str = ""
    representative_projects: str = ""
    full_info: str = ""
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "school": self.school,
            "lab": self.lab,
            "name": self.name,
            "research_direction": self.research_direction,
            "recruitment_preference": self.recruitment_preference,
            "academic_style": self.academic_style,
            "training_method": self.training_method,
            "students_background": self.students_background,
            "recent_papers": self.recent_papers,
            "representative_projects": self.representative_projects,
            "full_info": self.full_info,
            "references": self.references,
        }


class AdvisorService:
    """
    导师服务
    
    处理导师信息搜索和格式化
    """
    
    SEARCH_ASPECTS = {
        "p1": [
            {"key": "research_direction", "name": "研究方向"},
            {"key": "recruitment_preference", "name": "招生偏好"},
        ],
        "p2": [
            {"key": "academic_style", "name": "学术风格"},
            {"key": "training_method", "name": "培养方式"},
            {"key": "students_background", "name": "在读学生履历"},
        ],
        "p3": [
            {"key": "recent_papers", "name": "近期论文"},
            {"key": "representative_projects", "name": "代表项目"},
        ],
    }
    
    def __init__(
        self,
        api_keys: List[str],
        model: str = "qwen-plus",
    ):
        self.api_keys = api_keys
        self.model = model
        self._key_index = 0
    
    def _get_client(self, key_index: Optional[int] = None) -> OpenAI:
        """获取 OpenAI 客户端"""
        if key_index is None:
            key = self.api_keys[self._key_index % len(self.api_keys)]
            self._key_index += 1
        else:
            key = self.api_keys[key_index % len(self.api_keys)]
        
        return OpenAI(
            api_key=key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    
    def build_reference_links(self, school: str, advisor_name: str) -> List[str]:
        """构建搜索参考链接"""
        keyword = f"{school} {advisor_name}".strip()
        q = quote_plus(keyword)
        
        return [
            f"https://www.baidu.com/s?wd={q}",
            f"https://scholar.google.com/scholar?q={q}",
            f"https://dblp.org/search?q={q}",
            f"https://kns.cnki.net/kns8s?kw={q}",
            f"https://www.researchgate.net/search/publication?q={q}",
            f"https://xueshu.baidu.com/s?wd={q}",
        ]
    
    async def verify_advisor(self, school: str, advisor_name: str) -> Dict[str, Any]:
        """验证导师是否存在"""
        prompt = f"""请确认{school}是否存在名为"{advisor_name}"的导师/教师：

【任务】
1. 在学校官网教师名录中查找
2. 在学术数据库中搜索该导师的论文
3. 确认该导师的基本身份（职称、院系）

【返回格式】
如果找到，返回：职称、所在院系、主要研究方向
如果确实不存在，返回：未找到该导师信息"""
        
        def _call():
            client = self._get_client(0)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                extra_body={
                    "enable_search": True,
                    "search_options": {"forced_search": True, "search_strategy": "pro"}
                }
            )
            return response.choices[0].message.content.strip()
        
        try:
            result = await asyncio.to_thread(_call)
            
            if "未找到该导师信息" in result or "不存在" in result:
                return {"exists": False, "info": result}
            
            return {"exists": True, "info": result}
        except Exception as e:
            return {"exists": None, "info": None, "error": str(e)}
    
    async def search_aspect(
        self,
        school: str,
        advisor_name: str,
        aspect_key: str,
        aspect_name: str,
    ) -> Dict[str, Any]:
        """搜索单个方面的信息"""
        prompt = f"""联网搜索{school} {advisor_name}导师的{aspect_name}，返回具体事实：

【必须包含】具体信息，不要使用模糊表述
【禁止】编造不存在的信息
【格式】直接列出事实，80字以内"""
        
        def _call():
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                extra_body={
                    "enable_search": True,
                    "search_options": {"forced_search": True, "search_strategy": "pro"}
                }
            )
            return response.choices[0].message.content.strip()
        
        try:
            result = await asyncio.to_thread(_call)
            return {"key": aspect_key, "name": aspect_name, "success": True, "data": result}
        except Exception as e:
            return {"key": aspect_key, "name": aspect_name, "success": False, "error": str(e)}
    
    async def search_advisor(
        self,
        school: str,
        lab: str = "",
        advisor_name: str = "",
    ) -> Dict[str, Any]:
        """
        搜索导师信息
        
        Args:
            school: 学校名称
            lab: 实验室名称（可选）
            advisor_name: 导师姓名
            
        Returns:
            Dict: 搜索结果
        """
        school = school.strip()
        advisor_name = advisor_name.strip()
        
        if not school and not advisor_name:
            return {"success": False, "error": "请至少提供学校或导师姓名之一"}
        
        references = self.build_reference_links(school, advisor_name)
        
        # 验证导师
        verify_result = await self.verify_advisor(school, advisor_name)
        
        if verify_result.get("exists") == False:
            return {
                "success": False,
                "error": f"未找到 {school} {advisor_name} 导师的信息",
                "references": references,
            }
        
        # 搜索各个方面
        all_results = {}
        tasks = []
        
        for priority, aspects in self.SEARCH_ASPECTS.items():
            for aspect in aspects:
                tasks.append(
                    self.search_aspect(
                        school,
                        advisor_name,
                        aspect["key"],
                        aspect["name"],
                    )
                )
        
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result["success"] and result.get("data"):
                all_results[result["key"]] = result["data"]
        
        # 格式化完整信息
        full_info = self._format_full_info(all_results)
        
        return {
            "success": True,
            "data": full_info,
            "details": all_results,
            "references": references,
        }
    
    def _format_full_info(self, results: Dict[str, str]) -> str:
        """格式化完整信息"""
        section_names = {
            "research_direction": "【研究方向】",
            "recruitment_preference": "【招生偏好】",
            "academic_style": "【学术风格】",
            "training_method": "【培养方式】",
            "students_background": "【在读学生】",
            "recent_papers": "【近期论文】",
            "representative_projects": "【代表项目】"
        }
        
        sections = []
        for key, name in section_names.items():
            if key in results and results[key]:
                sections.append(f"{name}\n{results[key]}")
        
        return "\n\n".join(sections) if sections else "未能获取到导师信息"
    
    def format_for_prompt(
        self,
        advisor_text: str,
        school: str = "",
        lab: str = "",
        advisor_name: str = "",
    ) -> str:
        """格式化为 prompt 注入格式"""
        if not advisor_text:
            return ""
        
        meta_lines = []
        if school:
            meta_lines.append(f"学校: {school}")
        if lab:
            meta_lines.append(f"实验室: {lab}")
        if advisor_name:
            meta_lines.append(f"导师: {advisor_name}")
        
        meta_block = "\n".join(meta_lines)
        if meta_block:
            meta_block += "\n\n"
        
        return f"""【面试导师信息】
{meta_block}{advisor_text}

请根据上述导师的研究方向和学术背景，在面试中提出针对性的专业问题，考察候选人与该导师研究方向的匹配度。
"""
