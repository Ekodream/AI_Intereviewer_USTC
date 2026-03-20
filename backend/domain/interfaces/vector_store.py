"""
向量存储接口 - 定义向量数据库的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """搜索结果"""
    content: str
    metadata: Dict[str, Any]
    score: float
    
    
@dataclass
class Document:
    """文档实体"""
    content: str
    metadata: Dict[str, Any]


class VectorStore(ABC):
    """
    向量存储抽象基类
    
    定义向量数据库的标准接口。
    所有向量存储实现（如 Chroma、Faiss 等）都必须实现此接口。
    """
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Document],
        *,
        collection_name: str = "default",
    ) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
            collection_name: 集合名称
            
        Returns:
            List[str]: 文档 ID 列表
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        collection_name: str = "default",
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            collection_name: 集合名称
            top_k: 返回结果数量
            filter: 元数据过滤条件
            
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        *,
        collection_name: str = "default",
    ) -> bool:
        """
        删除文档
        
        Args:
            ids: 要删除的文档 ID 列表
            collection_name: 集合名称
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def get_collection_stats(
        self,
        collection_name: str = "default",
    ) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Dict: 统计信息（文档数量等）
        """
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        pass
