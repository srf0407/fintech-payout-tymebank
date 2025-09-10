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

logger = get_logger(__name__)

security_scheme = HTTPBearer(
    scheme_name="JWT",
    description="JWT access token for authentication",
    auto_error=False
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    Raises HTTPException if token is invalid or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = verify_access_token(credentials.credentials)
        
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    Returns None if no token provided or invalid token.
    """
    if not credentials:
        return None
    
    try:
        token_data = verify_access_token(credentials.credentials)
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
        
        if x_timestamp:
            if not verify_webhook_timestamp(x_timestamp, settings.webhook_timeout_seconds):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Webhook timestamp is invalid or too old"
                )
        
        if x_signature_type.startswith("hmac_"):
            algorithm = x_signature_type.replace("hmac_", "")
            if not verify_webhook_signature_hmac(body, x_signature, settings.webhook_secret, algorithm):
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


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
ActiveUser = Annotated[User, Depends(require_active_user)]
CorrelationID = Annotated[str, Depends(get_correlation_id)]
WebhookSignature = Annotated[Dict[str, Any], Depends(verify_webhook_signature)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
