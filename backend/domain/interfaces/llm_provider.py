"""
LLM 提供者接口 - 定义大语言模型服务的抽象接口
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Optional


class LLMProvider(ABC):
    """
    LLM 提供者抽象基类
    
    定义大语言模型服务的标准接口，支持流式和非流式对话。
    所有 LLM 实现（如 DashScope、OpenAI 等）都必须实现此接口。
    """
    
    @abstractmethod
    async def stream_chat(
        self,
        history: List[Dict[str, str]],
        message: str,
        system_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        流式对话接口
        
        Args:
            history: 对话历史，格式为 [{"role": "user/assistant", "content": "..."}]
            message: 当前用户消息
            system_prompt: 系统提示词
            temperature: 生成温度，控制随机性
            max_tokens: 最大生成 token 数
            
        Yields:
            str: 生成的文本片段
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        history: List[Dict[str, str]],
        message: str,
        system_prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        单次对话接口（非流式）
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大生成 token 数
            
        Returns:
            str: 完整的生成文本
        """
        pass
    
    @abstractmethod
    async def chat_with_thinking(
        self,
        history: List[Dict[str, str]],
        message: str,
        system_prompt: str,
        *,
        enable_thinking: bool = True,
    ) -> str:
        """
        带思考过程的对话接口
        
        用于需要深度推理的场景（如生成评估报告）
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            enable_thinking: 是否启用思考模式
            
        Returns:
            str: 完整的生成文本
        """
        pass
