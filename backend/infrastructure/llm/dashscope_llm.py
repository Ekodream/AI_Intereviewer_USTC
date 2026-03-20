"""
DashScope LLM 实现 - 阿里云大语言模型服务
"""

import logging
from typing import AsyncIterator, List, Dict, Optional

from openai import AsyncOpenAI

from backend.domain.interfaces.llm_provider import LLMProvider
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class DashScopeLLM(LLMProvider):
    """
    阿里云 DashScope LLM 实现
    
    基于 OpenAI 兼容接口调用阿里云的大语言模型服务
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 DashScope LLM
        
        Args:
            api_key: API 密钥（可选，默认从配置读取）
            base_url: API 基础 URL（可选，默认从配置读取）
            model: 模型名称（可选，默认从配置读取）
        """
        self._api_key = api_key or settings.DASHSCOPE_API_KEY
        self._base_url = base_url or settings.LLM_BASE_URL
        self._model = model or settings.LLM_MODEL
        
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
    
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
        流式对话
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大生成 token 数
            
        Yields:
            str: 生成的文本片段
        """
        messages = self._build_messages(history, message, system_prompt)
        
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "stream": True,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            response = await self._client.chat.completions.create(**kwargs)
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"DashScope stream_chat error: {e}")
            raise
    
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
        单次对话（非流式）
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            temperature: 生成温度
            max_tokens: 最大生成 token 数
            
        Returns:
            str: 完整的生成文本
        """
        messages = self._build_messages(history, message, system_prompt)
        
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            response = await self._client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"DashScope chat error: {e}")
            raise
    
    async def chat_with_thinking(
        self,
        history: List[Dict[str, str]],
        message: str,
        system_prompt: str,
        *,
        enable_thinking: bool = True,
    ) -> str:
        """
        带思考过程的对话
        
        用于需要深度推理的场景（如生成评估报告）
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            enable_thinking: 是否启用思考模式
            
        Returns:
            str: 完整的生成文本
        """
        messages = self._build_messages(history, message, system_prompt)
        
        try:
            # 使用支持思考的模型（如果可用）
            model = "qwq-plus" if enable_thinking else self._model
            
            kwargs = {
                "model": model,
                "messages": messages,
            }
            
            # 添加思考模式参数（如果支持）
            if enable_thinking:
                kwargs["extra_body"] = {"enable_thinking": True}
            
            response = await self._client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"DashScope chat_with_thinking error: {e}")
            # 降级到普通对话
            return await self.chat(history, message, system_prompt)
    
    def _build_messages(
        self,
        history: List[Dict[str, str]],
        message: str,
        system_prompt: str,
    ) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Args:
            history: 对话历史
            message: 当前用户消息
            system_prompt: 系统提示词
            
        Returns:
            List[Dict]: OpenAI 格式的消息列表
        """
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加历史对话
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
