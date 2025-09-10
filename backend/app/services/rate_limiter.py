"""
In-memory rate limiting service for API endpoints.
Implements sliding window rate limiting with configurable limits per user.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from ..core.config import settings
from ..core.logging import get_logger
from ..core.security import generate_correlation_id

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter.
    
    Uses a deque to store timestamps of requests within the window.
    Automatically cleans up old entries to prevent memory leaks.
    """
    
    def __init__(self, window_size_seconds: int = 60, max_requests: int = None):
        self.window_size_seconds = window_size_seconds
        self.max_requests = max_requests or settings.rate_limit_per_minute
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._cleanup_threshold = 1000 
        
        logger.info("Rate limiter initialized", extra={
            "window_size_seconds": window_size_seconds,
            "max_requests": self.max_requests
        })
    
    def _cleanup_old_entries(self, user_id: str, current_time: float):
        """Remove entries older than the window from the user's deque."""
        window_start = current_time - self.window_size_seconds
        
        user_window = self._windows[user_id]
        while user_window and user_window[0] < window_start:
            user_window.popleft()
    
    def _cleanup_inactive_users(self):
        """Remove users with empty windows to prevent memory leaks."""
        if len(self._windows) > self._cleanup_threshold:
            inactive_users = [
                user_id for user_id, window in self._windows.items()
                if not window
            ]
            
            for user_id in inactive_users:
                del self._windows[user_id]
            
            logger.debug("Cleaned up inactive users", extra={
                "cleaned_count": len(inactive_users),
                "remaining_users": len(self._windows)
            })
    
    def check_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        current_time = time.time()
        
        self._cleanup_old_entries(user_id, current_time)
        
        user_window = self._windows[user_id]
        current_requests = len(user_window)
        
        logger.debug("Rate limit check", extra={
            "correlation_id": correlation_id,
            "user_id": user_id,
            "current_requests": current_requests,
            "max_requests": self.max_requests,
            "window_size_seconds": self.window_size_seconds
        })
        
        if current_requests >= self.max_requests:
            oldest_request_time = user_window[0] if user_window else current_time
            retry_after = int(oldest_request_time + self.window_size_seconds - current_time)
            
            logger.warning("Rate limit exceeded", extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "current_requests": current_requests,
                "max_requests": self.max_requests,
                "retry_after_seconds": retry_after
            })
            
            raise RateLimitExceeded(
                f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_size_seconds} seconds.",
                retry_after
            )
        
        user_window.append(current_time)
        
        self._cleanup_inactive_users()
        
        remaining_requests = self.max_requests - current_requests - 1
        reset_time = int(current_time + self.window_size_seconds)
        
        logger.debug("Rate limit check passed", extra={
            "correlation_id": correlation_id,
            "user_id": user_id,
            "remaining_requests": remaining_requests,
            "reset_time": reset_time
        })
        
        return {
            "remaining_requests": remaining_requests,
            "reset_time": reset_time
        }
    
    def get_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """
        Get current rate limit information for a user without consuming a request.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with current requests, remaining requests, and reset time
        """
        current_time = time.time()
        self._cleanup_old_entries(user_id, current_time)
        
        user_window = self._windows[user_id]
        current_requests = len(user_window)
        remaining_requests = max(0, self.max_requests - current_requests)
        
        if user_window:
            oldest_request_time = user_window[0]
            reset_time = int(oldest_request_time + self.window_size_seconds)
        else:
            reset_time = int(current_time)
        
        return {
            "current_requests": current_requests,
            "remaining_requests": remaining_requests,
            "max_requests": self.max_requests,
            "reset_time": reset_time,
            "window_size_seconds": self.window_size_seconds
        }
    
    def reset_user_limit(self, user_id: str):
        """Reset rate limit for a specific user."""
        if user_id in self._windows:
            del self._windows[user_id]
            logger.info("Rate limit reset for user", extra={"user_id": user_id})
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics."""
        total_users = len(self._windows)
        total_requests = sum(len(window) for window in self._windows.values())
        
        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "max_requests_per_user": self.max_requests,
            "window_size_seconds": self.window_size_seconds
        }


class RateLimiterService:
    """Service for managing rate limiting across different endpoints."""
    
    def __init__(self):
        self.payout_limiter = SlidingWindowRateLimiter(
            window_size_seconds=60,
            max_requests=settings.rate_limit_per_minute
        )
        
    
        
        logger.info("Rate limiter service initialized", extra={
            "payout_rate_limit": settings.rate_limit_per_minute
        })
    
    def check_payout_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for payout creation.
        
        Args:
            user_id: User identifier
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.payout_limiter.check_rate_limit(user_id, correlation_id)
    
    def get_payout_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get payout rate limit information for a user."""
        return self.payout_limiter.get_rate_limit_info(user_id)
    
    def reset_payout_rate_limit(self, user_id: str):
        """Reset payout rate limit for a user."""
        self.payout_limiter.reset_user_limit(user_id)
    
    def get_service_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for all rate limiters."""
        return {
            "payout_limiter": self.payout_limiter.get_stats()
        }


rate_limiter_service = RateLimiterService()


def create_rate_limit_exception(retry_after: int, correlation_id: str) -> HTTPException:
    """Create a standardized rate limit HTTP exception."""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": retry_after,
            "correlation_id": correlation_id
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + retry_after)
        }
    )
