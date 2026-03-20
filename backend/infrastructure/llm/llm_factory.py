"""
LLM 工厂 - 创建 LLM 提供者实例
"""

from typing import Optional, Literal

from backend.domain.interfaces.llm_provider import LLMProvider
from backend.infrastructure.llm.dashscope_llm import DashScopeLLM


LLMProviderType = Literal["dashscope", "openai"]


class LLMFactory:
    """
    LLM 工厂类
    
    根据配置创建对应的 LLM 提供者实例
    """
    
    _instances: dict[str, LLMProvider] = {}
    
    @classmethod
    def create(
        cls,
        provider: LLMProviderType = "dashscope",
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        use_singleton: bool = True,
    ) -> LLMProvider:
        """
        创建 LLM 提供者实例
        
        Args:
            provider: 提供者类型
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            use_singleton: 是否使用单例模式
            
        Returns:
            LLMProvider: LLM 提供者实例
        """
        cache_key = f"{provider}_{model or 'default'}"
        
        if use_singleton and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        if provider == "dashscope":
            instance = DashScopeLLM(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
        elif provider == "openai":
            # 可以扩展支持 OpenAI
            # instance = OpenAILLM(api_key=api_key, model=model)
            raise NotImplementedError("OpenAI provider not implemented yet")
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        if use_singleton:
            cls._instances[cache_key] = instance
        
        return instance
    
    @classmethod
    def get_default(cls) -> LLMProvider:
        """
        获取默认的 LLM 提供者
        
        Returns:
            LLMProvider: 默认的 LLM 提供者实例
        """
        return cls.create("dashscope")
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除缓存的实例"""
        cls._instances.clear()
