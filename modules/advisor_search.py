"""
导师信息搜索模块
使用 DashScope OpenAI 兼容模式的联网搜索功能搜索导师信息
"""

from openai import OpenAI

try:
    from config import DASHSCOPE_API_KEY
except ImportError:
    DASHSCOPE_API_KEY = "sk-af8e9af4aae340bd86178117f7f3f33c"


def search_advisor_info(school, advisor_name):
    """
    联网搜索导师信息
    
    Args:
        school: 学校名称
        advisor_name: 导师姓名
    
    Returns:
        dict: 导师信息字典，包含：
            - success: 是否搜索成功
            - data: 导师信息数据
            - error: 错误信息（如果失败）
    """
    school = school.strip()
    advisor_name = advisor_name.strip()
    
    if not school or not advisor_name:
        return {
            "success": False,
            "data": None,
            "error": "学校和导师姓名不能为空"
        }
    
    print(f"🔍 开始联网搜索：{school} - {advisor_name}")
    
    try:
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        search_prompt = f"""请通过联网搜索以下导师的信息，重点搜集与**研究生面试**相关的内容：

学校：{school}
导师姓名：{advisor_name}

**请重点搜索以下信息（按重要性排序）：**

1. **研究方向**（最重要）：主要研究领域、技术方向、关键词
2. **学术风格**：偏理论还是偏工程？注重基础还是创新？
3. **招生偏好**：喜欢什么样的学生？考察重点是什么？
4. **培养方式**：严格管理还是放养？实验室氛围如何？
5. **近期论文/兴趣**
6. **代表论文/项目**（简单提及即可）

**要求：**
- 返回一段连贯的文字，300-500 字
- 不要 JSON 格式，不要分点列表
- 语言简洁、专业
- 不确定的信息不要写
- **重点突出与面试相关的内容**

**示例：**
"陈恩红，中国科学技术大学教授，主要研究方向为数据挖掘、机器学习和社会网络分析。学术风格偏工程应用，注重学生实践能力培养，在顶级会议发表论文 50 余篇。招生偏好计算机基础扎实、有较强编程能力的学生，面试中会深入考察数据结构和算法理解。实验室氛围活跃，项目多与企业合作，适合想走工业界路线的学生。"
"""

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": search_prompt}],
            extra_body={
                "enable_search": True,
                "search_options": {
                    "forced_search": True,
                    "search_strategy": "pro"
                }
            }
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 清理可能的 markdown 标记
        if result_text.startswith("```"):
            lines = result_text.split('\n')
            if lines[0].startswith("```"):
                result_text = '\n'.join(lines[1:])
            if lines[-1].strip() == "```":
                result_text = '\n'.join(lines[:-1])
            result_text = result_text.strip()
        
        print(f"✅ 成功搜索到 {school} - {advisor_name} 的信息")
        
        return {
            "success": True,
            "data": result_text,
            "error": None
        }
            
    except Exception as e:
        print(f"❌ 搜索失败：{e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


def format_advisor_info_for_prompt(advisor_text):
    """
    将导师信息文本包装为 prompt 注入格式
    
    Args:
        advisor_text: 导师信息文本（字符串）
    
    Returns:
        str: 包装后的 prompt 文本
    """
    if not advisor_text:
        return ""
    
    return f"""
【面试导师信息】
{advisor_text}

请根据上述导师的研究方向和学术背景，在面试中提出针对性的专业问题，考察候选人与该导师研究方向的匹配度。
"""


# 测试函数
if __name__ == "__main__":
    print("测试导师搜索功能...")
    result = search_advisor_info("中国科学技术大学", "陈恩红")
    if result["success"]:
        print("\n✅ 搜索成功！")
        print(format_advisor_info_for_prompt(result["data"]))
    else:
        print(f"\n❌ 搜索失败：{result['error']}")
