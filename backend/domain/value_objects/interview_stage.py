"""
面试阶段枚举 - 定义面试的各个阶段
"""

from enum import IntEnum


class InterviewStage(IntEnum):
    """
    面试阶段枚举
    
    面试流程按照以下阶段顺序进行：
    0. 开始 - 面试开场
    1. 自我介绍 - 候选人自我介绍
    2. 经历深挖 - 深入了解候选人经历
    3. 基础知识 - 专业基础知识考察
    4. 代码 - 编程能力考察
    5. 科研动机 - 了解科研兴趣和动机
    6. 科研潜力 - 评估科研潜力
    7. 综合追问 - 综合问题追问
    8. 学生反问 - 候选人提问环节
    9. 结束 - 面试结束
    """
    START = 0           # 开始
    SELF_INTRO = 1      # 自我介绍
    EXPERIENCE = 2      # 经历深挖
    BASIC_KNOWLEDGE = 3 # 基础知识
    CODING = 4          # 代码
    RESEARCH_MOTIVE = 5 # 科研动机
    RESEARCH_POTENTIAL = 6  # 科研潜力
    FOLLOW_UP = 7       # 综合追问
    CANDIDATE_QA = 8    # 学生反问
    END = 9             # 结束
    
    @classmethod
    def from_int(cls, value: int) -> "InterviewStage":
        """从整数创建阶段枚举"""
        if 0 <= value <= 9:
            return cls(value)
        raise ValueError(f"Invalid interview stage: {value}")
    
    @property
    def display_name(self) -> str:
        """获取阶段的中文显示名称"""
        names = {
            0: "开始",
            1: "自我介绍",
            2: "经历深挖",
            3: "基础知识",
            4: "代码",
            5: "科研动机",
            6: "科研潜力",
            7: "综合追问",
            8: "学生反问",
            9: "结束",
        }
        return names.get(self.value, "未知阶段")
    
    def is_terminal(self) -> bool:
        """判断是否为终止阶段"""
        return self == InterviewStage.END
    
    def can_advance_to(self, target: "InterviewStage") -> bool:
        """判断是否可以推进到目标阶段"""
        # 只能向后推进，不能回退
        return target.value > self.value
