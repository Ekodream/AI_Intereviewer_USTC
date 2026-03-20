"""
面试风格枚举 - 定义面试官的不同风格
"""

from enum import Enum
from typing import Dict


class InterviewStyle(str, Enum):
    """
    面试风格枚举
    
    定义三种不同的面试官风格：
    - GENTLE: 温和型 - 鼓励为主，氛围轻松
    - NORMAL: 正常型 - 平衡提问，专业客观
    - PRESSURE: 压力型 - 追问较多，考验抗压能力
    """
    GENTLE = "gentle"       # 温和型
    NORMAL = "normal"       # 正常型
    PRESSURE = "pressure"   # 压力型
    
    @property
    def display_name(self) -> str:
        """获取风格的中文显示名称"""
        names = {
            "gentle": "温和型",
            "normal": "正常型",
            "pressure": "压力型",
        }
        return names.get(self.value, "未知风格")
    
    @property
    def description(self) -> str:
        """获取风格的描述"""
        descriptions = {
            "gentle": "以鼓励为主，营造轻松的面试氛围，给予充分的时间思考",
            "normal": "专业客观的提问方式，平衡难度和引导",
            "pressure": "较多追问和质疑，考验候选人的抗压能力和应变能力",
        }
        return descriptions.get(self.value, "")
    
    def get_style_config(self) -> Dict[str, any]:
        """获取风格对应的配置参数"""
        configs = {
            "gentle": {
                "follow_up_intensity": 0.3,     # 追问强度
                "encouragement_level": 0.8,     # 鼓励程度
                "time_pressure": 0.2,           # 时间压力
                "difficulty_scaling": 0.8,      # 难度系数
            },
            "normal": {
                "follow_up_intensity": 0.5,
                "encouragement_level": 0.5,
                "time_pressure": 0.5,
                "difficulty_scaling": 1.0,
            },
            "pressure": {
                "follow_up_intensity": 0.8,
                "encouragement_level": 0.2,
                "time_pressure": 0.8,
                "difficulty_scaling": 1.2,
            },
        }
        return configs.get(self.value, configs["normal"])
