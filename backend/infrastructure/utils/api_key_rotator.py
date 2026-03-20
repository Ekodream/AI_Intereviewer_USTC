"""
API Key 轮询器 - 管理多个 API Key 的轮询和并发控制
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional
import threading


@dataclass
class KeyState:
    """单个 Key 的状态"""
    key: str
    last_used: float = 0.0
    current_concurrent: int = 0
    total_calls: int = 0
    total_errors: int = 0


class APIKeyRotator:
    """
    API Key 轮询器
    
    管理多个 API Key 的轮询，支持：
    - 最小调用间隔控制
    - 最大并发数控制
    - 线程安全
    """
    
    def __init__(
        self,
        api_keys: List[str],
        min_interval: float = 1.5,
        max_concurrent: int = 4,
    ):
        """
        初始化轮询器
        
        Args:
            api_keys: API Key 列表
            min_interval: 单个 Key 的最小调用间隔（秒）
            max_concurrent: 单个 Key 的最大并发数
        """
        if not api_keys:
            raise ValueError("API keys list cannot be empty")
        
        self._keys = [KeyState(key=k) for k in api_keys]
        self._min_interval = min_interval
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()
        self._current_index = 0
    
    def get_key(self) -> Optional[str]:
        """
        获取一个可用的 API Key
        
        Returns:
            Optional[str]: 可用的 API Key，如果没有可用 Key 返回 None
        """
        with self._lock:
            now = time.time()
            
            # 尝试找到一个可用的 Key
            for _ in range(len(self._keys)):
                key_state = self._keys[self._current_index]
                
                # 检查间隔和并发限制
                time_since_last = now - key_state.last_used
                if (time_since_last >= self._min_interval and 
                    key_state.current_concurrent < self._max_concurrent):
                    
                    key_state.last_used = now
                    key_state.current_concurrent += 1
                    key_state.total_calls += 1
                    
                    key = key_state.key
                    self._current_index = (self._current_index + 1) % len(self._keys)
                    return key
                
                # 移动到下一个 Key
                self._current_index = (self._current_index + 1) % len(self._keys)
            
            return None
    
    def release_key(self, key: str, success: bool = True) -> None:
        """
        释放一个 API Key（调用完成后）
        
        Args:
            key: 要释放的 API Key
            success: 调用是否成功
        """
        with self._lock:
            for key_state in self._keys:
                if key_state.key == key:
                    key_state.current_concurrent = max(0, key_state.current_concurrent - 1)
                    if not success:
                        key_state.total_errors += 1
                    break
    
    async def get_key_async(self, timeout: float = 30.0) -> Optional[str]:
        """
        异步获取一个可用的 API Key（带等待）
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            Optional[str]: 可用的 API Key，超时返回 None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            key = self.get_key()
            if key:
                return key
            await asyncio.sleep(0.1)
        
        return None
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                "total_keys": len(self._keys),
                "keys": [
                    {
                        "key": k.key[:8] + "...",  # 只显示前8位
                        "concurrent": k.current_concurrent,
                        "total_calls": k.total_calls,
                        "total_errors": k.total_errors,
                    }
                    for k in self._keys
                ]
            }


class AsyncAPIKeyRotator:
    """
    异步 API Key 轮询器
    
    使用 asyncio.Lock 实现的异步版本
    """
    
    def __init__(
        self,
        api_keys: List[str],
        min_interval: float = 1.5,
        max_concurrent: int = 4,
    ):
        if not api_keys:
            raise ValueError("API keys list cannot be empty")
        
        self._keys = [KeyState(key=k) for k in api_keys]
        self._min_interval = min_interval
        self._max_concurrent = max_concurrent
        self._lock = asyncio.Lock()
        self._current_index = 0
    
    async def get_key(self, timeout: float = 30.0) -> Optional[str]:
        """
        获取一个可用的 API Key
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            Optional[str]: 可用的 API Key，超时返回 None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with self._lock:
                now = time.time()
                
                for _ in range(len(self._keys)):
                    key_state = self._keys[self._current_index]
                    
                    time_since_last = now - key_state.last_used
                    if (time_since_last >= self._min_interval and 
                        key_state.current_concurrent < self._max_concurrent):
                        
                        key_state.last_used = now
                        key_state.current_concurrent += 1
                        key_state.total_calls += 1
                        
                        key = key_state.key
                        self._current_index = (self._current_index + 1) % len(self._keys)
                        return key
                    
                    self._current_index = (self._current_index + 1) % len(self._keys)
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def release_key(self, key: str, success: bool = True) -> None:
        """释放一个 API Key"""
        async with self._lock:
            for key_state in self._keys:
                if key_state.key == key:
                    key_state.current_concurrent = max(0, key_state.current_concurrent - 1)
                    if not success:
                        key_state.total_errors += 1
                    break
