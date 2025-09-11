"""
FastAPI dependencies for authentication, authorization, and security.
"""

from typing import Optional, Dict, Any, Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import verify_access_token, generate_correlation_id
from ..core.logging import get_logger
from ..db.session import get_db
from ..models.user import User
from ..services.auth_service import AuthService
from ..services.webhook_service import WebhookService
from ..services.rate_limiter import (
    rate_limiter_service,
    get_client_identifier,
    create_rate_limit_exception,
    RateLimitExceeded
)

logger = get_logger(__name__)

security_scheme = HTTPBearer(
    scheme_name="JWT",
    description="JWT access token for authentication",
    auto_error=False
)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    Supports both Authorization header and HTTP-only cookies.
    Raises HTTPException if token is invalid or user not found.
    """
    token = None
  
    if credentials:
        token = credentials.credentials
        logger.info("Token found in Authorization header")
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]
        logger.info("Token found in HTTP-only cookie")
    else:
        logger.warning("No token found in Authorization header or cookies", extra={
            "has_credentials": bool(credentials),
            "cookies": list(request.cookies.keys())
        })
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = verify_access_token(token)
        
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_google_id(token_data["google_id"])
        
        if not user:
            logger.warning("User not found for valid token", extra={
                "google_id": token_data["google_id"],
                "user_id": token_data.get("sub")
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Authentication error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    Supports both Authorization header and HTTP-only cookies.
    Returns None if no token provided or invalid token.
    """
    token = None
    
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies["access_token"]
    
    if not token:
        return None
    
    try:
        token_data = verify_access_token(token)
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_google_id(token_data["google_id"])
        return user
    except Exception:
        return None


async def get_correlation_id(
    request: Request,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
) -> str:
    """
    Get or generate correlation ID for request tracing.
    """
    if x_correlation_id:
        return x_correlation_id
    
    if hasattr(request.state, "correlation_id"):
        return request.state.correlation_id
    
    correlation_id = generate_correlation_id()
    request.state.correlation_id = correlation_id
    return correlation_id


async def verify_webhook_signature(
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_signature_type: str = Header(default="hmac_sha256", alias="X-Signature-Type"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
) -> Dict[str, Any]:
    """
    Verify webhook signature and return signature data.
    Raises HTTPException if signature verification fails.
    """
    from ..core.security import (
        verify_webhook_signature_hmac,
        verify_webhook_signature_jwt,
        verify_webhook_timestamp,
        WebhookVerificationError
    )
    from ..core.config import settings
    
    try:
        body = await request.body()
        
        # Log the signature verification attempt
        logger.info("Verifying webhook signature", extra={
            "signature_type": x_signature_type,
            "signature": x_signature[:20] + "..." if len(x_signature) > 20 else x_signature,
            "body_length": len(body),
            "correlation_id": getattr(request.state, "correlation_id", None)
        })
        
        if x_timestamp:
            if not verify_webhook_timestamp(x_timestamp, settings.webhook_timeout_seconds):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Webhook timestamp is invalid or too old"
                )
        
        if x_signature_type.startswith("hmac_"):
            algorithm = x_signature_type.replace("hmac_", "")
            if not verify_webhook_signature_hmac(body, x_signature, settings.webhook_secret, algorithm):
                logger.warning("HMAC signature verification failed", extra={
                    "signature_type": x_signature_type,
                    "algorithm": algorithm,
                    "correlation_id": getattr(request.state, "correlation_id", None)
                })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
            signature_data = {"type": x_signature_type, "verified": True}
            
        elif x_signature_type == "jwt":
            payload = verify_webhook_signature_jwt(x_signature, settings.webhook_secret)
            signature_data = {"type": "jwt", "verified": True, "payload": payload}
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported signature type: {x_signature_type}"
            )
        
        logger.info("Webhook signature verified successfully", extra={
            "signature_type": x_signature_type,
            "correlation_id": getattr(request.state, "correlation_id", None)
        })
        
        return signature_data
        
    except WebhookVerificationError as e:
        logger.warning("Webhook signature verification failed", extra={
            "error": str(e),
            "signature_type": x_signature_type,
            "correlation_id": getattr(request.state, "correlation_id", None)
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signature verification failed"
        )
    except Exception as e:
        logger.error("Webhook verification error", extra={
            "error": str(e),
            "signature_type": x_signature_type,
            "correlation_id": getattr(request.state, "correlation_id", None)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification error"
        )


async def require_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require an active user (additional checks can be added here).
    """
    return current_user


async def get_auth_service(
    db: AsyncSession = Depends(get_db)
) -> AuthService:
    """
    Get authentication service instance.
    """
    return AuthService(db)


async def get_webhook_service(
    db: AsyncSession = Depends(get_db)
) -> WebhookService:
    """
    Get webhook service instance.
    """
    return WebhookService(db)


# Type aliases for dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
ActiveUser = Annotated[User, Depends(require_active_user)]
CorrelationID = Annotated[str, Depends(get_correlation_id)]
WebhookSignature = Annotated[Dict[str, Any], Depends(verify_webhook_signature)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]

# Rate limiting dependencies for auth endpoints
async def check_auth_login_rate_limit(
    request: Request,
    correlation_id: CorrelationID
) -> None:
    """Check rate limit for auth login attempts."""
    try:
        client_id = get_client_identifier(request)
        rate_limiter_service.check_auth_login_rate_limit(client_id, correlation_id)
    except RateLimitExceeded as e:
        raise create_rate_limit_exception(e.retry_after, correlation_id, "login")


async def check_auth_callback_rate_limit(
    request: Request,
    correlation_id: CorrelationID
) -> None:
    """Check rate limit for auth callback attempts."""
    try:
        client_id = get_client_identifier(request)
        rate_limiter_service.check_auth_callback_rate_limit(client_id, correlation_id)
    except RateLimitExceeded as e:
        raise create_rate_limit_exception(e.retry_after, correlation_id, "callback")


async def check_token_refresh_rate_limit(
    request: Request,
    correlation_id: CorrelationID,
    current_user: CurrentUser
) -> None:
    """Check rate limit for token refresh attempts."""
    try:
        user_id = str(current_user.id)
        rate_limiter_service.check_token_refresh_rate_limit(user_id, correlation_id)
    except RateLimitExceeded as e:
        raise create_rate_limit_exception(e.retry_after, correlation_id, "refresh")


async def check_auth_general_rate_limit(
    request: Request,
    correlation_id: CorrelationID,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> None:
    """Check rate limit for general auth endpoints."""
    try:
        if current_user:
            user_id = str(current_user.id)
        else:
            user_id = get_client_identifier(request)
        
        rate_limiter_service.check_auth_general_rate_limit(user_id, correlation_id)
    except RateLimitExceeded as e:
        raise create_rate_limit_exception(e.retry_after, correlation_id, "general")


AuthLoginRateLimit = Annotated[None, Depends(check_auth_login_rate_limit)]
AuthCallbackRateLimit = Annotated[None, Depends(check_auth_callback_rate_limit)]
TokenRefreshRateLimit = Annotated[None, Depends(check_token_refresh_rate_limit)]
AuthGeneralRateLimit = Annotated[None, Depends(check_auth_general_rate_limit)]


