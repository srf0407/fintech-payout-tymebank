"""
Authentication schemas for OAuth 2.0 flows and JWT tokens.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class OAuthLoginRequest(BaseModel):
    """Request to initiate OAuth login flow."""
    
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    
    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Redirect URI must be a valid HTTP/HTTPS URL")
        return v


class OAuthLoginResponse(BaseModel):
    """Response containing OAuth authorization URL and state."""
    
    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state parameter")
    code_verifier: str = Field(..., description="PKCE code verifier (store securely)")
    expires_at: datetime = Field(..., description="When the state expires")




class GoogleUserInfo(BaseModel):
    """Google user information from OAuth provider."""
    
    id: str = Field(..., description="Google user ID")
    email: str = Field(..., description="User email address")
    verified_email: bool = Field(..., description="Whether email is verified")
    name: str = Field(..., description="User full name")
    given_name: Optional[str] = Field(None, description="User first name")
    family_name: Optional[str] = Field(None, description="User last name")
    picture: Optional[str] = Field(None, description="User profile picture URL")
    locale: Optional[str] = Field(None, description="User locale")


class TokenData(BaseModel):
    """JWT token payload data."""
    
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    picture: Optional[str] = Field(None, description="User picture URL")
    google_id: str = Field(..., description="Google user ID")
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")
    jti: str = Field(..., description="JWT ID for token uniqueness")
    iss: str = Field(..., description="Token issuer")
    aud: str = Field(..., description="Token audience")


class TokenResponse(BaseModel):
    """Response containing access token and user information."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: "UserResponse" = Field(..., description="User information")


class UserResponse(BaseModel):
    """User information response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="User ID")
    google_id: str = Field(..., description="Google user ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    picture_url: Optional[str] = Field(None, description="User picture URL")
    created_at: datetime = Field(..., description="User creation timestamp")


class AuthErrorResponse(BaseModel):
    """Authentication error response."""
    
    error: str = Field(..., description="Error code")
    error_description: str = Field(..., description="Human-readable error description")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Request to logout user."""
    
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class LogoutResponse(BaseModel):
    """Response after successful logout."""
    
    message: str = Field(..., description="Logout confirmation message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


TokenResponse.model_rebuild()
