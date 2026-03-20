"""
存储接口 - 定义各类存储服务的抽象接口
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any
from datetime import datetime


T = TypeVar("T")


class Storage(ABC, Generic[T]):
    """
    通用存储抽象基类
    
    定义 CRUD 操作的标准接口
    """
    
    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """
        根据 ID 获取实体
        
        Args:
            id: 实体 ID
            
        Returns:
            Optional[T]: 实体对象，不存在返回 None
        """
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> str:
        """
        保存实体
        
        Args:
            entity: 实体对象
            
        Returns:
            str: 实体 ID
        """
        pass
    
    @abstractmethod
    async def update(self, id: str, entity: T) -> bool:
        """
        更新实体
        
        Args:
            id: 实体 ID
            entity: 更新后的实体对象
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        删除实体
        
        Args:
            id: 实体 ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def list(
        self,
        *,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """
        列出实体
        
        Args:
            filter: 过滤条件
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            List[T]: 实体列表
        """
        pass


class SessionStorage(ABC):
    """
    会话存储抽象基类
    
    定义会话数据存储的标准接口，支持 TTL 过期
    """
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Optional[Dict]: 会话数据，不存在或已过期返回 None
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        session_id: str,
        data: Dict[str, Any],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        设置会话数据
        
        Args:
            session_id: 会话 ID
            data: 会话数据
            ttl_seconds: 过期时间（秒）
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        部分更新会话数据
        
        Args:
            session_id: 会话 ID
            updates: 要更新的字段
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    async def touch(self, session_id: str) -> bool:
        """
        刷新会话过期时间
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        pass


class FileStorage(ABC):
    """
    文件存储抽象基类
    
    定义文件存储的标准接口
    """
    
    @abstractmethod
    async def save(
        self,
        data: bytes,
        filename: str,
        *,
        directory: Optional[str] = None,
    ) -> str:
        """
        保存文件
        
        Args:
            data: 文件数据
            filename: 文件名
            directory: 子目录（可选）
            
        Returns:
            str: 文件路径
        """
        pass
    
    @abstractmethod
    async def read(self, path: str) -> Optional[bytes]:
        """
        读取文件
        
        Args:
            path: 文件路径
            
        Returns:
            Optional[bytes]: 文件数据，不存在返回 None
        """
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        删除文件
        
        Args:
            path: 文件路径
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            path: 文件路径
            
        Returns:
            bool: 是否存在
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        directory: str,
        *,
        pattern: Optional[str] = None,
    ) -> List[str]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件名模式（可选，如 "*.pdf"）
            
        Returns:
            List[str]: 文件路径列表
        """
        pass
