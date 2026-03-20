"""
向量嵌入接口 - 定义文本向量化服务的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """
    向量嵌入提供者抽象基类
    
    定义文本向量化服务的标准接口。
    所有嵌入模型实现（如 DashScope Embedding 等）都必须实现此接口。
    """
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为向量
        
        Args:
            text: 要向量化的文本
            
        Returns:
            List[float]: 向量表示
        """
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            List[List[float]]: 向量列表
        """
        pass
    
    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """获取向量维度"""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """获取嵌入模型名称"""
        pass
