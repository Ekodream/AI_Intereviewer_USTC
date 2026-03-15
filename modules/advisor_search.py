"""
导师信息搜索模块
使用 DashScope OpenAI 兼容模式的联网搜索能力检索导师信息。
"""

from openai import OpenAI

from config import DASHSCOPE_API_KEY, LLM_BASE_URL


def search_advisor_info(school: str, lab: str, advisor_name: str) -> dict:
    """联网搜索导师信息并返回结构化结果。"""
    school = (school or "").strip()
    lab = (lab or "").strip()
    advisor_name = (advisor_name or "").strip()

    if not school or not lab or not advisor_name:
        return {
            "success": False,
            "data": None,
            "error": "学校、实验室和导师姓名不能为空",
        }

    try:
        client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=LLM_BASE_URL)
        search_prompt = f"""请通过联网搜索导师信息，并重点提炼对研究生面试有帮助的结论。

学校: {school}
实验室: {lab}
导师姓名: {advisor_name}

请重点覆盖:
1) 研究方向与关键词
2) 学术风格(偏理论/偏工程)
3) 招生偏好与常见考察重点
4) 实验室培养方式与协作要求
5) 近年代表性论文或项目方向(简述)

输出要求:
- 300-500 字中文
- 连贯文字，不要 JSON，不要表格
- 不确定信息不要编造
- 重点突出“面试中应该重点准备什么”
"""

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": search_prompt}],
            extra_body={
                "enable_search": True,
                "search_options": {
                    "forced_search": True,
                    "search_strategy": "pro",
                },
            },
        )

        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        if not content:
            return {
                "success": False,
                "data": None,
                "error": "未检索到有效导师信息",
            }

        return {
            "success": True,
            "data": content,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e),
        }


def format_advisor_info_for_prompt(advisor_text: str, school: str, lab: str, advisor_name: str) -> str:
    """将导师信息组装为可注入系统提示词的文本。"""
    advisor_text = (advisor_text or "").strip()
    school = (school or "").strip()
    lab = (lab or "").strip()
    advisor_name = (advisor_name or "").strip()

    if not advisor_text:
        return ""

    return f"""【导师画像信息】
学校: {school}
实验室: {lab}
导师: {advisor_name}

{advisor_text}
"""
