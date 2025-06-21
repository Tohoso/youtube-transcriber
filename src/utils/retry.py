"""Retry functionality for network operations."""

import asyncio
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

from loguru import logger


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], tuple] = Exception,
) -> Callable:
    """Async retry decorator."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}, "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


class RetryManager:
    """Manage retry logic for operations."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
    ):
        """Initialize retry manager."""
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
    
    async def execute(
        self,
        func: Callable,
        *args: Any,
        exceptions: Union[Type[Exception], tuple] = Exception,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    wait_time = self.delay * (self.backoff ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed: {e}")
        
        raise last_exception