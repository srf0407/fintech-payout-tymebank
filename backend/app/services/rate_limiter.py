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
from ..core.errors import create_rate_limit_error

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
        
        self.auth_login_limiter = SlidingWindowRateLimiter(
            window_size_seconds=settings.auth_login_window_minutes * 60,
            max_requests=settings.auth_login_rate_limit
        )
        
        self.auth_callback_limiter = SlidingWindowRateLimiter(
            window_size_seconds=settings.auth_callback_window_minutes * 60,
            max_requests=settings.auth_callback_rate_limit
        )
        
        self.token_refresh_limiter = SlidingWindowRateLimiter(
            window_size_seconds=settings.auth_refresh_window_minutes * 60,
            max_requests=settings.auth_refresh_rate_limit
        )
        
        self.auth_general_limiter = SlidingWindowRateLimiter(
            window_size_seconds=settings.auth_general_window_minutes * 60,
            max_requests=settings.auth_general_rate_limit
        )
        
        logger.info("Rate limiter service initialized", extra={
            "payout_rate_limit": settings.rate_limit_per_minute,
            "auth_login_limit": settings.auth_login_rate_limit,
            "auth_callback_limit": settings.auth_callback_rate_limit,
            "token_refresh_limit": settings.auth_refresh_rate_limit,
            "auth_general_limit": settings.auth_general_rate_limit
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
    
    def check_auth_login_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for auth login attempts.
        
        Args:
            user_id: User identifier (IP address for anonymous users)
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.auth_login_limiter.check_rate_limit(user_id, correlation_id)
    
    def check_auth_callback_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for auth callback attempts.
        
        Args:
            user_id: User identifier (IP address for anonymous users)
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.auth_callback_limiter.check_rate_limit(user_id, correlation_id)
    
    def check_token_refresh_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for token refresh attempts.
        
        Args:
            user_id: User identifier
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.token_refresh_limiter.check_rate_limit(user_id, correlation_id)
    
    def check_auth_general_rate_limit(
        self,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Check rate limit for general auth endpoints.
        
        Args:
            user_id: User identifier
            correlation_id: Correlation ID for logging
            
        Returns:
            Dict with remaining requests and reset time
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        return self.auth_general_limiter.check_rate_limit(user_id, correlation_id)
    
    def get_auth_login_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get auth login rate limit information for a user."""
        return self.auth_login_limiter.get_rate_limit_info(user_id)
    
    def get_auth_callback_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get auth callback rate limit information for a user."""
        return self.auth_callback_limiter.get_rate_limit_info(user_id)
    
    def get_token_refresh_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get token refresh rate limit information for a user."""
        return self.token_refresh_limiter.get_rate_limit_info(user_id)
    
    def get_auth_general_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get general auth rate limit information for a user."""
        return self.auth_general_limiter.get_rate_limit_info(user_id)
    
    def reset_auth_rate_limits(self, user_id: str):
        """Reset all auth rate limits for a user."""
        self.auth_login_limiter.reset_user_limit(user_id)
        self.auth_callback_limiter.reset_user_limit(user_id)
        self.token_refresh_limiter.reset_user_limit(user_id)
        self.auth_general_limiter.reset_user_limit(user_id)
        logger.info("All auth rate limits reset for user", extra={"user_id": user_id})
    
    def get_service_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for all rate limiters."""
        return {
            "payout_limiter": self.payout_limiter.get_stats(),
            "auth_login_limiter": self.auth_login_limiter.get_stats(),
            "auth_callback_limiter": self.auth_callback_limiter.get_stats(),
            "token_refresh_limiter": self.token_refresh_limiter.get_stats(),
            "auth_general_limiter": self.auth_general_limiter.get_stats()
        }


rate_limiter_service = RateLimiterService()


def get_client_identifier(request) -> str:
    """
    Get a unique identifier for rate limiting.
    Uses IP address for anonymous users, user ID for authenticated users.
    """
    if hasattr(request.state, 'user_id') and request.state.user_id:
        return str(request.state.user_id)
    
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}"


def create_rate_limit_exception(retry_after: int, correlation_id: str, limit_type: str = "general") -> HTTPException:
    """Create a standardized rate limit HTTP exception."""
    limits = {
        "login": settings.auth_login_rate_limit,
        "callback": settings.auth_callback_rate_limit,
        "refresh": settings.auth_refresh_rate_limit,
        "general": settings.auth_general_rate_limit,
        "payout": settings.rate_limit_per_minute
    }
    
    limit = limits.get(limit_type, settings.auth_general_rate_limit)
    
    return create_rate_limit_error(
        retry_after=retry_after,
        limit_type=limit_type,
        correlation_id=correlation_id
    )
