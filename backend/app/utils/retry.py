"""
Retry utility with exponential backoff and jitter for handling transient errors.
Implements bounded exponential backoff with jitter to prevent thundering herd problems.
"""

import asyncio
import random
import time
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps

import httpx
from fastapi import HTTPException, status

from ..core.logging import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_status_codes: set[int] = None,
        retryable_exceptions: tuple[Type[Exception], ...] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_status_codes = retryable_status_codes or {429, 500, 502, 503, 504}
        self.retryable_exceptions = retryable_exceptions or (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.RemoteProtocolError,
            httpx.PoolTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.ConnectTimeout,
            httpx.PoolTimeout,
        )


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for the given attempt using exponential backoff with jitter.
    
    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        jitter_factor = random.uniform(0.5, 1.5)
        delay *= jitter_factor
    
    return delay


def is_retryable_error(error: Exception, config: RetryConfig) -> bool:
    """
    Check if an error is retryable based on configuration.
    
    Args:
        error: Exception to check
        config: Retry configuration
        
    Returns:
        True if error is retryable
    """
    if isinstance(error, HTTPException):
        return error.status_code in config.retryable_status_codes
    
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in config.retryable_status_codes
    
    return isinstance(error, config.retryable_exceptions)


async def retry_async(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff and jitter.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        config: Retry configuration (uses default if None)
        correlation_id: Correlation ID for logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            logger.debug("Retry attempt", extra={
                "correlation_id": correlation_id,
                "attempt": attempt + 1,
                "max_retries": config.max_retries,
                "function": func.__name__
            })
            
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info("Function succeeded after retry", extra={
                    "correlation_id": correlation_id,
                    "attempt": attempt + 1,
                    "function": func.__name__
                })
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if not is_retryable_error(e, config):
                logger.warning("Non-retryable error encountered", extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
                raise e
            
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                
                logger.warning("Retryable error encountered, retrying", extra={
                    "correlation_id": correlation_id,
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "delay_seconds": delay,
                    "function": func.__name__
                })
                
                await asyncio.sleep(delay)
            else:
                logger.error("All retry attempts exhausted", extra={
                    "correlation_id": correlation_id,
                    "attempts": config.max_retries + 1,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
    
    raise RetryError(
        f"Function {func.__name__} failed after {config.max_retries + 1} attempts",
        last_exception,
        config.max_retries + 1
    )


def retry_sync(
    func: Callable[..., Any],
    *args,
    config: Optional[RetryConfig] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Retry a synchronous function with exponential backoff and jitter.
    
    Args:
        func: Synchronous function to retry
        *args: Positional arguments for the function
        config: Retry configuration (uses default if None)
        correlation_id: Correlation ID for logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            logger.debug("Retry attempt", extra={
                "correlation_id": correlation_id,
                "attempt": attempt + 1,
                "max_retries": config.max_retries,
                "function": func.__name__
            })
            
            result = func(*args, **kwargs)
            
            if attempt > 0:
                logger.info("Function succeeded after retry", extra={
                    "correlation_id": correlation_id,
                    "attempt": attempt + 1,
                    "function": func.__name__
                })
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if not is_retryable_error(e, config):
                logger.warning("Non-retryable error encountered", extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
                raise e
            
            if attempt < config.max_retries:
                delay = calculate_delay(attempt, config)
                
                logger.warning("Retryable error encountered, retrying", extra={
                    "correlation_id": correlation_id,
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "delay_seconds": delay,
                    "function": func.__name__
                })
                
                time.sleep(delay)
            else:
                logger.error("All retry attempts exhausted", extra={
                    "correlation_id": correlation_id,
                    "attempts": config.max_retries + 1,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "function": func.__name__
                })
    
    raise RetryError(
        f"Function {func.__name__} failed after {config.max_retries + 1} attempts",
        last_exception,
        config.max_retries + 1
    )


def retry_decorator(
    config: Optional[RetryConfig] = None,
    correlation_id_key: str = "correlation_id"
):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        config: Retry configuration (uses default if None)
        correlation_id_key: Key to extract correlation ID from kwargs
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                correlation_id = kwargs.get(correlation_id_key)
                return await retry_async(func, *args, config=config, correlation_id=correlation_id, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                correlation_id = kwargs.get(correlation_id_key)
                return retry_sync(func, *args, config=config, correlation_id=correlation_id, **kwargs)
            return sync_wrapper
    
    return decorator


PAYMENT_API_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_status_codes={429, 500, 502, 503, 504, 408}
)

WEBHOOK_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    retryable_status_codes={429, 500, 502, 503, 504}
)

QUICK_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    base_delay=0.1,
    max_delay=1.0,
    exponential_base=2.0,
    jitter=True,
    retryable_status_codes={429, 500, 502, 503, 504}
)
