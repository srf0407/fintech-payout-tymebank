"""
Authentication routes for OAuth 2.0 flows.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse

from ..deps import (
    AuthServiceDep, 
    CorrelationID, 
    get_current_user,
    AuthLoginRateLimit,
    AuthCallbackRateLimit,
    TokenRefreshRateLimit,
    AuthGeneralRateLimit
)
from ...schemas.auth import (
    OAuthLoginRequest,
    OAuthLoginResponse,
    TokenResponse,
    AuthErrorResponse,
    LogoutRequest,
    LogoutResponse,
    UserResponse
)
from ...core.logging import get_logger
from ...core.security import sanitize_log_data
from ...core.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=OAuthLoginResponse)
async def initiate_login(
    request_data: OAuthLoginRequest,
    auth_service: AuthServiceDep,
    correlation_id: CorrelationID,
    _: AuthLoginRateLimit
) -> OAuthLoginResponse:
    """
    Initiate OAuth 2.0 login flow with secure state and PKCE.
    
    This endpoint:
    - Generates cryptographically secure state parameter
    - Creates PKCE code verifier and challenge
    - Returns Google OAuth authorization URL
    - Stores security parameters for callback verification
    """
    try:
        logger.info("OAuth login initiated", extra={
            "correlation_id": correlation_id,
            "redirect_uri": request_data.redirect_uri
        })
        
        auth_data = await auth_service.initiate_oauth_login(request_data.redirect_uri)
        
        return OAuthLoginResponse(
            authorization_url=auth_data["authorization_url"],
            state=auth_data["state"],
            code_verifier=auth_data["code_verifier"],
            expires_at=auth_data["expires_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login initiation failed", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login"
        )




@router.get("/callback")
async def oauth_callback(
    request: Request,
    auth_service: AuthServiceDep,
    correlation_id: CorrelationID,
    _: AuthCallbackRateLimit
) -> RedirectResponse:
    """
    Handle OAuth callback via GET request (for browser redirects).
    
    This endpoint:
    - Extracts authorization code and state from query parameters
    - Validates state parameter
    - Exchanges code for tokens
    - Redirects to frontend with token or error
    """
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        if error:
            logger.warning("OAuth error received", extra={
                "correlation_id": correlation_id,
                "error": error,
                "error_description": request.query_params.get("error_description")
            })
            return RedirectResponse(
                url=f"{settings.frontend_url}/auth/callback?error={error}&correlation_id={correlation_id}"
            )
        
        if not code or not state:
            logger.warning("Missing OAuth parameters", extra={
                "correlation_id": correlation_id,
                "has_code": bool(code),
                "has_state": bool(state)
            })
            return RedirectResponse(
                url=f"{settings.frontend_url}/auth/callback?error=missing_parameters&correlation_id={correlation_id}"
            )
        
        redirect_uri = f"{request.base_url}auth/callback"
        
        logger.info("Processing OAuth callback", extra={
            "correlation_id": correlation_id,
            "code": code[:8] + "...",
            "state": state[:8] + "..."
        })
        
        token_response = await auth_service.handle_oauth_callback(
            code=code,
            state=state,
            redirect_uri=redirect_uri
        )
        
        response = RedirectResponse(
            url=f"{settings.frontend_url}/dashboard"
        )
        
        response.set_cookie(
            key="access_token",
            value=token_response.access_token,
            httponly=True,           
            secure=not settings.debug,  
            samesite="strict", 
            max_age=settings.access_token_expire_minutes * 60,
            path="/"
        )
        
        logger.info("OAuth callback successful, cookie set", extra={
            "correlation_id": correlation_id,
            "user_id": token_response.user.id
        })
        
        return response
        
    except HTTPException as e:
        logger.error("OAuth callback failed", extra={
            "correlation_id": correlation_id,
            "status_code": e.status_code,
            "detail": e.detail
        })
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?error=oauth_failed&correlation_id={correlation_id}"
        )
    except Exception as e:
        logger.error("Unexpected error in OAuth callback", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?error=server_error&correlation_id={correlation_id}"
        )




@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    correlation_id: CorrelationID,
    auth_service: AuthServiceDep,
    _: TokenRefreshRateLimit,
    current_user = Depends(get_current_user)
) -> TokenResponse:
    """
    Refresh user's access token.
    
    This endpoint:
    - Validates current JWT token from cookie
    - Generates new access token with updated expiration
    - Sets new token in HTTP-only cookie
    - Returns new token and user information
    """
    try:
        logger.info("Token refresh requested", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        token_response = await auth_service.refresh_user_token(current_user)
        
        response = JSONResponse(content=token_response.model_dump())
        
        response.set_cookie(
            key="access_token",
            value=token_response.access_token,
            httponly=True,         
            secure=not settings.debug,  
            samesite="strict",     
            max_age=settings.access_token_expire_minutes * 60,
            path="/"
        )
        
        logger.info("Token refreshed successfully", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    request_data: LogoutRequest,
    correlation_id: CorrelationID,
    auth_service: AuthServiceDep,
    _: AuthGeneralRateLimit,
    current_user = Depends(get_current_user)
) -> LogoutResponse:
    """
    Logout user and invalidate session.
    
    This endpoint:
    - Validates current user authentication
    - Performs logout operations
    - Clears HTTP-only cookie
    - Returns confirmation message
    """
    try:
        logger.info("User logout requested", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        logout_data = await auth_service.logout_user(current_user)
        
        response = JSONResponse(content=LogoutResponse(
            message=logout_data["message"],
            correlation_id=correlation_id
        ).model_dump())
        
        response.delete_cookie(
            key="access_token",
            path="/",
            samesite="strict"
        )
        
        logger.info("User logged out successfully", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Logout failed", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    correlation_id: CorrelationID,
    _: AuthGeneralRateLimit,
    current_user = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.
    
    This endpoint:
    - Validates JWT token
    - Returns current user's profile information
    """
    try:
        logger.info("User info requested", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        return UserResponse.model_validate(current_user)
        
    except Exception as e:
        logger.error("Failed to get user info", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


