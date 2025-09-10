"""
Authentication routes for OAuth 2.0 flows.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse

from ..deps import AuthServiceDep, CorrelationID, get_current_user
from ...schemas.auth import (
    OAuthLoginRequest,
    OAuthLoginResponse,
    OAuthCallbackRequest,
    TokenResponse,
    AuthErrorResponse,
    LogoutRequest,
    LogoutResponse,
    UserResponse
)
from ...core.logging import get_logger
from ...core.security import sanitize_log_data

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=OAuthLoginResponse)
async def initiate_login(
    request_data: OAuthLoginRequest,
    auth_service: AuthServiceDep,
    correlation_id: CorrelationID
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


@router.post("/callback", response_model=TokenResponse)
async def handle_callback(
    request_data: OAuthCallbackRequest,
    auth_service: AuthServiceDep,
    correlation_id: CorrelationID
) -> TokenResponse:
    """
    Handle OAuth 2.0 callback and exchange authorization code for tokens.
    
    This endpoint:
    - Validates state parameter for CSRF protection
    - Exchanges authorization code for access token using PKCE
    - Fetches user information from Google
    - Creates or updates user in database
    - Returns JWT access token
    """
    try:
        logger.info("OAuth callback received", extra={
            "correlation_id": correlation_id,
            "state": request_data.state[:8] + "...",
            "redirect_uri": request_data.redirect_uri
        })
        
        token_response = await auth_service.handle_oauth_callback(
            code=request_data.code,
            state=request_data.state,
            code_verifier=request_data.code_verifier,
            redirect_uri=request_data.redirect_uri
        )
        
        logger.info("OAuth callback successful", extra={
            "correlation_id": correlation_id,
            "user_id": token_response.user.id
        })
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OAuth callback failed", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth callback processing failed"
        )


@router.get("/callback/google")
async def google_callback(
    request: Request,
    auth_service: AuthServiceDep,
    correlation_id: CorrelationID
) -> RedirectResponse:
    """
    Handle Google OAuth callback via GET request (for browser redirects).
    
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
                url=f"http://localhost:3000/auth/callback?error={error}&correlation_id={correlation_id}"
            )
        
        if not code or not state:
            logger.warning("Missing OAuth parameters", extra={
                "correlation_id": correlation_id,
                "has_code": bool(code),
                "has_state": bool(state)
            })
            return RedirectResponse(
                url=f"http://localhost:3000/auth/callback?error=missing_parameters&correlation_id={correlation_id}"
            )
        
        redirect_uri = f"{request.base_url}auth/callback/google"
        
        from ...core.security import generate_code_verifier
        code_verifier = generate_code_verifier()
        
        logger.info("Processing Google OAuth callback", extra={
            "correlation_id": correlation_id,
            "code": code[:8] + "...",
            "state": state[:8] + "..."
        })
        
        token_response = await auth_service.handle_oauth_callback(
            code=code,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri
        )
        
        return RedirectResponse(
            url=f"http://localhost:3000/auth/callback?success=true&token={token_response.access_token}&correlation_id={correlation_id}"
        )
        
    except HTTPException as e:
        logger.error("Google OAuth callback failed", extra={
            "correlation_id": correlation_id,
            "status_code": e.status_code,
            "detail": e.detail
        })
        return RedirectResponse(
            url=f"http://localhost:3000/auth/callback?error=oauth_failed&correlation_id={correlation_id}"
        )
    except Exception as e:
        logger.error("Unexpected error in Google OAuth callback", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        return RedirectResponse(
            url=f"http://localhost:3000/auth/callback?error=server_error&correlation_id={correlation_id}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    correlation_id: CorrelationID,
    auth_service: AuthServiceDep,
    current_user = Depends(get_current_user)
) -> TokenResponse:
    """
    Refresh user's access token.
    
    This endpoint:
    - Validates current JWT token
    - Generates new access token with updated expiration
    - Returns new token and user information
    """
    try:
        logger.info("Token refresh requested", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        token_response = await auth_service.refresh_user_token(current_user)
        
        logger.info("Token refreshed successfully", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        return token_response
        
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
    request_data: LogoutRequest,
    correlation_id: CorrelationID,
    auth_service: AuthServiceDep,
    current_user = Depends(get_current_user)
) -> LogoutResponse:
    """
    Logout user and invalidate session.
    
    This endpoint:
    - Validates current user authentication
    - Performs logout operations
    - Returns confirmation message
    """
    try:
        logger.info("User logout requested", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        logout_data = await auth_service.logout_user(current_user)
        
        logger.info("User logged out successfully", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id)
        })
        
        return LogoutResponse(
            message=logout_data["message"],
            correlation_id=correlation_id
        )
        
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
