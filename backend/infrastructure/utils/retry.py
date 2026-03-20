"""
重试装饰器 - 为异步函数提供自动重试功能
"""

import asyncio
import functools
import logging
from typing import Callable, Optional, Type, Tuple, Any

logger = logging.getLogger(__name__)


def retry_async(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    异步重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟（秒）
        backoff: 延迟增长系数
        exceptions: 触发重试的异常类型
        on_retry: 重试时的回调函数
        
    Returns:
        装饰器函数
        
    Example:
        @retry_async(max_retries=3, delay=1.0)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_sync(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    同步重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟（秒）
        backoff: 延迟增长系数
        exceptions: 触发重试的异常类型
        on_retry: 重试时的回调函数
        
    Returns:
        装饰器函数
    """
    import time
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


async def retry_operation(
    operation: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    """
    重试一个异步操作
    
    Args:
        operation: 要重试的异步函数
        max_retries: 最大重试次数
        delay: 初始重试延迟
        backoff: 延迟增长系数
        exceptions: 触发重试的异常类型
        
    Returns:
        操作的返回值
        
    Example:
        result = await retry_operation(
            lambda: fetch_data(url),
            max_retries=3,
            delay=1.0
        )
    """
    current_delay = delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")
    
    raise last_exception
