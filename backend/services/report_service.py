"""
报告服务 - 处理面试报告生成相关业务逻辑
"""

from typing import List, Dict, Optional, Any, Iterator
from openai import OpenAI


REPORT_SYSTEM_PROMPT = """你是一位资深技术面试评审专家。你的任务是对完整面试对话给出可执行、可追踪、可复训的评估报告。

请遵循以下规则：
1) 必须证据驱动：每个关键结论都要引用对话中的具体表现（可简述原话，不要编造）。
2) 必须量化：按权重给分，所有分项加总必须等于总分 100。
3) 必须可行动：改进建议要具体到"下一步怎么做、做到什么标准、如何验证"。
4) 保持客观克制，避免空泛赞美或打击式措辞。

## 评分维度（总分100）
1. 专业知识（30）
2. 科研潜力（30）
3. 综合素质（20）
4. 临场表现（10）
5. 反问质量（10）

## 输出格式（严格按此顺序）

# AI 面试评价报告

## 一、总体评分
- 总分: X/100
- 评级: `A(90-100) | B(80-89) | C(70-79) | D(60-69) | E(<60)`
- 一句话结论: 不超过30字

## 二、分维度评分与证据
### 1) 专业知识（X/30）
- 证据:
- 风险:

### 2) 科研潜力（X/30）
- 证据:
- 风险:

### 3) 综合素质（X/20）
- 证据:
- 风险:

### 4) 临场表现（X/10）
- 证据:
- 风险:

### 5) 反问质量（X/10）
- 证据:
- 风险:

## 三、关键亮点（最多3条）
- [亮点1]
- [亮点2]
- [亮点3]

## 四、关键短板（最多3条）
- [短板1]
- [短板2]
- [短板3]

## 五、30天改进计划
- Week 1:
- Week 2:
- Week 3:
- Week 4:

## 六、下一轮面试建议题单（3题）
1. [题目 + 目的]
2. [题目 + 目的]
3. [题目 + 目的]

## 七、结构化评分(JSON)
请在最后单独输出一个 ```json 代码块，字段固定为：
{
  "overall": 0,
  "grade": "",
  "dimensions": {
         "professional_knowledge": 0,
         "research_potential": 0,
         "comprehensive_quality": 0,
         "on_the_spot_performance": 0,
         "question_quality": 0
  },
  "risk_flags": [""],
  "next_focus": ["", "", ""]
}

注意：
- dimensions 五项必须和 overall 一致。
- JSON 必须可解析，不能带注释。
"""


class ReportService:
    """
    报告服务
    
    生成面试评价报告
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "qwen-max",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ):
        self.api_key = api_key
        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)
    
    def format_history(self, history: List[Dict[str, str]]) -> str:
        """将对话历史格式化为文本"""
        if not history:
            return "（无对话记录）"
        
        lines = []
        turn = 0
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                turn += 1
                lines.append(f"【第 {turn} 轮】")
                lines.append(f"候选人：{content}")
            elif role == "assistant":
                lines.append(f"导师：{content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_user_message(
        self,
        history: List[Dict[str, str]],
        resume_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建用户消息"""
        formatted_history = self.format_history(history)
        
        user_turns = sum(1 for msg in history if msg.get("role") == "user")
        assistant_turns = sum(1 for msg in history if msg.get("role") == "assistant")
        
        user_message = (
            f"以下是一段完整的技术面试对话记录，共 {user_turns} 轮候选人回答、"
            f"{assistant_turns} 轮导师提问。\n"
            f"请根据对话内容对被面试者的表现进行全面评价。\n\n"
            f"--- 面试对话记录 ---\n\n"
            f"{formatted_history}\n"
            f"--- 对话记录结束 ---"
        )
        
        # 添加简历匹配度评估
        if resume_analysis:
            basic = resume_analysis.get("basic_info", {})
            skills = resume_analysis.get("technical_skills", {})
            work = resume_analysis.get("work_experience", [])
            projects = resume_analysis.get("projects", [])
            assess = resume_analysis.get("assessment", {})
            
            resume_summary = f"""
--- 候选人简历摘要 ---
姓名：{basic.get('name', '未知')}
工作年限：{basic.get('years_of_experience', 0)}年
技术栈：{', '.join(skills.get('programming_languages', []) + skills.get('frameworks', [])[:5])}
技术深度评分：{assess.get('technical_depth_score', 0)}/10
技术广度评分：{assess.get('technical_breadth_score', 0)}/10
工作经历：{len(work)}段
项目经验：{len(projects)}个
--- 简历摘要结束 ---

请在评价报告中增加以下维度：

## 六、简历匹配度评估

### 1. 技术匹配度（XX / 10）
- 评估面试中展现的技术能力与简历描述的技能栈匹配程度
- 检查是否简历中提到的关键技术都在面试中得到了验证

### 2. 经验匹配度（XX / 10）
- 评估面试表现与简历中工作年限的匹配程度
- 检查项目经验的真实性和深度
- 识别是否存在简历夸大或面试表现不符的情况

### 3. 一致性评估
- 指出面试回答与简历描述一致的地方
- 标注可能存在的疑点或不一致之处
"""
            user_message += f"\n\n{resume_summary}"
        
        user_message += "\n\n请按要求的格式输出评价报告。"
        return user_message
    
    def generate_report(
        self,
        history: List[Dict[str, str]],
        resume_analysis: Optional[Dict[str, Any]] = None,
        enable_thinking: bool = True,
    ) -> str:
        """
        生成面试评价报告（非流式）
        
        Args:
            history: 对话历史
            resume_analysis: 简历分析结果
            enable_thinking: 是否开启思考模式
            
        Returns:
            str: 报告内容
        """
        if not history:
            return "⚠️ 没有对话记录，无法生成面试评价报告。"
        
        user_message = self._build_user_message(history, resume_analysis)
        
        messages = [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        
        try:
            request_params = {
                "model": self.model,
                "messages": messages,
            }
            
            if enable_thinking:
                request_params["extra_body"] = {"enable_thinking": True}
            
            completion = self._client.chat.completions.create(**request_params)
            
            if completion.choices and completion.choices[0].message:
                return completion.choices[0].message.content or "⚠️ 模型未返回有效内容。"
            else:
                return "⚠️ 模型返回为空，请稍后重试。"
                
        except Exception as e:
            raise RuntimeError(f"面试评价报告生成失败: {str(e)}") from e
    
    def generate_report_stream(
        self,
        history: List[Dict[str, str]],
        resume_analysis: Optional[Dict[str, Any]] = None,
        enable_thinking: bool = True,
    ) -> Iterator[str]:
        """
        流式生成面试评价报告
        
        Args:
            history: 对话历史
            resume_analysis: 简历分析结果
            enable_thinking: 是否开启思考模式
            
        Yields:
            str: 逐步累积的报告文本
        """
        if not history:
            yield "⚠️ 没有对话记录，无法生成面试评价报告。"
            return
        
        user_message = self._build_user_message(history, resume_analysis)
        
        messages = [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        
        try:
            request_params = {
                "model": self.model,
                "messages": messages,
                "stream": True,
            }
            
            if enable_thinking:
                request_params["extra_body"] = {"enable_thinking": True}
                request_params["stream_options"] = {"include_usage": True}
            
            completion = self._client.chat.completions.create(**request_params)
            
            full_response = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield full_response
                    
        except Exception as e:
            yield f"⚠️ 面试评价报告生成失败: {str(e)}"
    
    def append_reference_links(self, report: str, links: List[str]) -> str:
        """在报告末尾追加参考链接"""
        if not links:
            return report
        
        seen = set()
        unique_links = []
        for link in links:
            link = (link or "").strip()
            if link and link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        unique_links = unique_links[:12]
        
        if not unique_links:
            return report
        
        lines = [
            "",
            "---",
            "",
            "## 附录：导师搜索参考链接",
            "以下链接来自导师信息联网搜索阶段，供你复核和延伸阅读：",
        ]
        for idx, link in enumerate(unique_links, start=1):
            lines.append(f"{idx}. {link}")
        
        return (report or "").rstrip() + "\n" + "\n".join(lines) + "\n"
