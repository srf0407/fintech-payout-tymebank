"""
Centralized error handling with standardized error responses.
Provides specific error codes and user-friendly messages for frontend integration.
"""

from typing import Dict, Any, Optional
from enum import Enum
from fastapi import HTTPException, status

from .logging import get_logger

logger = get_logger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for frontend handling."""
    
    # Authentication errors (401) - No retry
    AUTH_REQUIRED = "auth_required"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    USER_NOT_FOUND = "user_not_found"
    
    # Validation errors (400) - No retry
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FORMAT = "invalid_format"
    
    # Rate limiting (429) - Manual retry
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    TOO_MANY_REQUESTS = "too_many_requests"
    
    # Server errors (500) - Auto retry
    INTERNAL_SERVER_ERROR = "internal_server_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    
    # Database errors (503) - Auto retry
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    DATABASE_QUERY_ERROR = "database_query_error"
    DATABASE_TIMEOUT = "database_timeout"
    
    # External service errors (503) - Auto retry
    EXTERNAL_SERVICE_UNAVAILABLE = "external_service_unavailable"
    EXTERNAL_SERVICE_TIMEOUT = "external_service_timeout"
    PAYMENT_PROVIDER_ERROR = "payment_provider_error"
    
    # Conflict errors (409) - No retry
    RESOURCE_CONFLICT = "resource_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    
    # Not found errors (404) - No retry
    RESOURCE_NOT_FOUND = "resource_not_found"
    PAYOUT_NOT_FOUND = "payout_not_found"


class ErrorResponse:
    """Standardized error response format."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        correlation_id: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.correlation_id = correlation_id
        self.retry_after = retry_after
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        response = {
            "error": self.error_code.value,
            "message": self.message,
            "correlation_id": self.correlation_id
        }
        
        if self.retry_after:
            response["retry_after"] = self.retry_after
        
        if self.details:
            response["details"] = self.details
        
        return response


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int,
    correlation_id: Optional[str] = None,
    retry_after: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> HTTPException:
    """
    Create a standardized HTTPException with error response.
    
    Args:
        error_code: Standardized error code
        message: User-friendly error message
        status_code: HTTP status code
        correlation_id: Correlation ID for tracing
        retry_after: Seconds to wait before retry (for retryable errors)
        details: Additional error details
        headers: Additional HTTP headers
        
    Returns:
        HTTPException with standardized error response
    """
    error_response = ErrorResponse(
        error_code=error_code,
        message=message,
        correlation_id=correlation_id,
        retry_after=retry_after,
        details=details
    )
    
    response_headers = headers or {}
    if retry_after:
        response_headers["Retry-After"] = str(retry_after)
    
    logger.error("Error response created", extra={
        "error_code": error_code.value,
        "status_code": status_code,
        "correlation_id": correlation_id,
        "retry_after": retry_after
    })
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.to_dict(),
        headers=response_headers
    )


# Predefined error responses for common scenarios
def create_auth_required_error(correlation_id: Optional[str] = None) -> HTTPException:
    """Create authentication required error."""
    return create_error_response(
        error_code=ErrorCode.AUTH_REQUIRED,
        message="Please log in to continue",
        status_code=status.HTTP_401_UNAUTHORIZED,
        correlation_id=correlation_id,
        headers={"WWW-Authenticate": "Bearer"}
    )


def create_token_expired_error(correlation_id: Optional[str] = None) -> HTTPException:
    """Create token expired error."""
    return create_error_response(
        error_code=ErrorCode.TOKEN_EXPIRED,
        message="Your session has expired. Please log in again",
        status_code=status.HTTP_401_UNAUTHORIZED,
        correlation_id=correlation_id,
        headers={"WWW-Authenticate": "Bearer"}
    )


def create_validation_error(
    message: str,
    correlation_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create validation error."""
    return create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        status_code=status.HTTP_400_BAD_REQUEST,
        correlation_id=correlation_id,
        details=details
    )


def create_rate_limit_error(
    retry_after: int,
    limit_type: str = "requests",
    correlation_id: Optional[str] = None
) -> HTTPException:
    """Create rate limit exceeded error."""
    return create_error_response(
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=f"Too many {limit_type}. Please wait {retry_after} seconds before trying again",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        correlation_id=correlation_id,
        retry_after=retry_after,
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Type": limit_type
        }
    )


def create_database_error(
    message: str = "Service temporarily unavailable",
    correlation_id: Optional[str] = None,
    retry_after: int = 30
) -> HTTPException:
    """Create database connection error."""
    return create_error_response(
        error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
        message=message,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        correlation_id=correlation_id,
        retry_after=retry_after,
        headers={"Retry-After": str(retry_after)}
    )


def create_external_service_error(
    service_name: str,
    correlation_id: Optional[str] = None,
    retry_after: int = 60
) -> HTTPException:
    """Create external service unavailable error."""
    return create_error_response(
        error_code=ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
        message=f"{service_name} is temporarily unavailable. Please try again later",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        correlation_id=correlation_id,
        retry_after=retry_after,
        headers={"Retry-After": str(retry_after)}
    )


def create_payment_provider_error(
    correlation_id: Optional[str] = None,
    retry_after: int = 30
) -> HTTPException:
    """Create payment provider error."""
    return create_error_response(
        error_code=ErrorCode.PAYMENT_PROVIDER_ERROR,
        message="Payment processing is temporarily unavailable. Please try again later",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        correlation_id=correlation_id,
        retry_after=retry_after,
        headers={"Retry-After": str(retry_after)}
    )


def create_internal_server_error(
    message: str = "Something went wrong. Please try again",
    correlation_id: Optional[str] = None
) -> HTTPException:
    """Create internal server error."""
    return create_error_response(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        correlation_id=correlation_id
    )


def create_not_found_error(
    resource_type: str,
    correlation_id: Optional[str] = None
) -> HTTPException:
    """Create resource not found error."""
    return create_error_response(
        error_code=ErrorCode.RESOURCE_NOT_FOUND,
        message=f"{resource_type} not found",
        status_code=status.HTTP_404_NOT_FOUND,
        correlation_id=correlation_id
    )


def create_conflict_error(
    message: str,
    correlation_id: Optional[str] = None
) -> HTTPException:
    """Create resource conflict error."""
    return create_error_response(
        error_code=ErrorCode.RESOURCE_CONFLICT,
        message=message,
        status_code=status.HTTP_409_CONFLICT,
        correlation_id=correlation_id
    )
