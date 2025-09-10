"""
Authentication service for OAuth 2.0 flows and user management.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from ..core.security import (
    create_access_token,
    exchange_oauth_code_for_token,
    get_google_user_info,
    generate_oauth_state,
    generate_oauth_nonce,
    validate_oauth_state
)
from ..core.config import settings
from ..core.logging import get_logger
from ..models.user import User
from ..schemas.auth import GoogleUserInfo, TokenResponse, UserResponse

logger = get_logger(__name__)


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def initiate_oauth_login(self, redirect_uri: str) -> Dict[str, Any]:
        """
        Initiate OAuth login flow with secure state and PKCE.
        Returns authorization URL and security parameters.
        """
        try:
            state = generate_oauth_state()
            nonce = generate_oauth_nonce()
            code_verifier = generate_code_verifier()
            
            auth_params = {
                "client_id": settings.google_client_id,
                "response_type": "code",
                "scope": " ".join(OAUTH_SCOPES),
                "redirect_uri": redirect_uri,
                "state": state,
                "nonce": nonce,
                "code_challenge": generate_code_challenge(code_verifier),
                "code_challenge_method": "S256",
                "access_type": "offline",
                "prompt": "consent"
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
            
            logger.info("OAuth login initiated", extra={
                "redirect_uri": redirect_uri,
                "state": state[:8] + "...",
                "nonce": nonce[:8] + "..."
            })
            
            return {
                "authorization_url": auth_url,
                "state": state,
                "code_verifier": code_verifier,
                "expires_at": datetime.utcnow() + timedelta(minutes=10)
            }
            
        except Exception as e:
            logger.error("Failed to initiate OAuth login", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate OAuth login"
            )
    
    async def handle_oauth_callback(
        self, 
        code: str, 
        state: str, 
        code_verifier: str, 
        redirect_uri: str
    ) -> TokenResponse:
        """
        Handle OAuth callback and exchange code for tokens.
        Creates or updates user and returns access token.
        """
        try:
            if not validate_oauth_state(state):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired state parameter"
                )
            
            token_data = await exchange_oauth_code_for_token(code, code_verifier, redirect_uri)
            
            user_info = await get_google_user_info(token_data["access_token"])
            google_user = GoogleUserInfo(**user_info)
            
            user = await self._create_or_update_user(google_user)
            
            token_payload = {
                "sub": str(user.id),
                "email": user.email,
                "name": user.name,
                "picture": user.picture_url,
                "google_id": user.google_id
            }
            
            access_token = create_access_token(token_payload)
            
            logger.info("OAuth callback successful", extra={
                "user_id": str(user.id),
                "email": user.email,
                "google_id": user.google_id
            })
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=UserResponse.model_validate(user)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("OAuth callback failed", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth callback processing failed"
            )
    
    async def _create_or_update_user(self, google_user: GoogleUserInfo) -> User:
        """
        Create or update user from Google user info.
        """
        try:
            stmt = select(User).where(User.google_id == google_user.id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.email = google_user.email
                user.name = google_user.name
                user.picture_url = google_user.picture
                logger.info("Updated existing user", extra={"user_id": str(user.id)})
            else:
                user = User(
                    google_id=google_user.id,
                    email=google_user.email,
                    name=google_user.name,
                    picture_url=google_user.picture
                )
                self.db.add(user)
                logger.info("Created new user", extra={"email": google_user.email})
            
            await self.db.commit()
            await self.db.refresh(user)
            
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create/update user", extra={
                "error": str(e),
                "google_id": google_user.id,
                "email": google_user.email
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or update user"
            )
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by ID", extra={
                "error": str(e),
                "user_id": str(user_id)
            })
            return None
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Get user by Google ID.
        """
        try:
            stmt = select(User).where(User.google_id == google_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by Google ID", extra={
                "error": str(e),
                "google_id": google_id
            })
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by email", extra={
                "error": str(e),
                "email": email
            })
            return None
    
    async def refresh_user_token(self, user: User) -> TokenResponse:
        """
        Refresh user's access token.
        """
        try:
            token_payload = {
                "sub": str(user.id),
                "email": user.email,
                "name": user.name,
                "picture": user.picture_url,
                "google_id": user.google_id
            }
            
            access_token = create_access_token(token_payload)
            
            logger.info("Token refreshed", extra={"user_id": str(user.id)})
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
                user=UserResponse.model_validate(user)
            )
            
        except Exception as e:
            logger.error("Failed to refresh token", extra={
                "error": str(e),
                "user_id": str(user.id)
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh token"
            )
    
    async def logout_user(self, user: User) -> Dict[str, str]:
        """
        Logout user (in a real implementation, you might revoke tokens).
        """
        try:
            logger.info("User logged out", extra={"user_id": str(user.id)})
            
            return {
                "message": "Successfully logged out",
                "user_id": str(user.id)
            }
            
        except Exception as e:
            logger.error("Logout failed", extra={
                "error": str(e),
                "user_id": str(user.id)
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )


OAUTH_SCOPES = ["openid", "email", "profile"]
