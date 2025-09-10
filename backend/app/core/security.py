"""
Security utilities for OAuth 2.0, JWT tokens, and webhook verification.
Implements secure OAuth flows with state, nonce, PKCE and HMAC/JWT webhook verification.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from .config import settings
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OAUTH_SCOPES = ["openid", "email", "profile"]
OAUTH_STATE_EXPIRE_MINUTES = 10
OAUTH_NONCE_EXPIRE_MINUTES = 10


class SecurityError(Exception):
    """Base security exception"""
    pass


class OAuthStateError(SecurityError):
    """OAuth state validation error"""
    pass


class WebhookVerificationError(SecurityError):
    """Webhook signature verification error"""
    pass


def generate_code_verifier() -> str:
    """
    Generate a cryptographically random code verifier for PKCE.
    Returns a URL-safe base64-encoded string.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')


def generate_code_challenge(code_verifier: str) -> str:
    """
    Generate code challenge from code verifier using SHA256.
    Returns a URL-safe base64-encoded string.
    """
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def generate_oauth_state() -> str:
    """
    Generate a cryptographically secure random state parameter.
    Includes timestamp for expiration validation.
    """
    timestamp = int(datetime.utcnow().timestamp())
    random_bytes = secrets.token_bytes(16)
    state_data = f"{timestamp}:{random_bytes.hex()}"
    signature = hmac.new(
        settings.secret_key.encode(),
        state_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{state_data}:{signature}"


def generate_oauth_nonce() -> str:
    """
    Generate a cryptographically secure random nonce.
    """
    return secrets.token_urlsafe(32)


def validate_oauth_state(state: str) -> bool:
    """
    Validate OAuth state parameter for integrity and expiration.
    Returns True if valid, raises OAuthStateError if invalid.
    """
    try:
        parts = state.split(':')
        if len(parts) != 3:
            raise OAuthStateError("Invalid state format")
        
        timestamp_str, random_hex, signature = parts
        
        state_data = f"{timestamp_str}:{random_hex}"
        expected_signature = hmac.new(
            settings.secret_key.encode(),
            state_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise OAuthStateError("Invalid state signature")
        
        timestamp = int(timestamp_str)
        current_time = int(datetime.utcnow().timestamp())
        if current_time - timestamp > OAUTH_STATE_EXPIRE_MINUTES * 60:
            raise OAuthStateError("State has expired")
        
        return True
        
    except (ValueError, IndexError) as e:
        raise OAuthStateError(f"Invalid state format: {e}")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with user data and expiration.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),  
        "iss": settings.app_name,  
        "aud": "fintech-payouts-api"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token.
    Returns the payload if valid, raises HTTPException if invalid.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=["HS256"],
            audience="fintech-payouts-api",
            issuer=settings.app_name
        )
        
        
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except JWTError as e:
        logger.warning("JWT verification failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def exchange_oauth_code_for_token(
    code: str, 
    code_verifier: str, 
    redirect_uri: str
) -> Dict[str, Any]:
    """
    Exchange OAuth authorization code for access token using PKCE.
    """
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error("OAuth token exchange failed", extra={
                "status_code": e.response.status_code,
                "response": e.response.text
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code for token"
            )
        except httpx.RequestError as e:
            logger.error("OAuth token exchange request failed", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OAuth service unavailable"
            )


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Fetch user information from Google using access token.
    """
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error("Google user info fetch failed", extra={
                "status_code": e.response.status_code,
                "response": e.response.text
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information from Google"
            )
        except httpx.RequestError as e:
            logger.error("Google user info request failed", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google service unavailable"
            )


def verify_webhook_signature_hmac(
    payload: bytes, 
    signature: str, 
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Verify webhook signature using HMAC.
    Supports sha256 and sha1 algorithms.
    """
    try:
        if "=" in signature:
            algo, sig = signature.split("=", 1)
            if algo != algorithm:
                raise WebhookVerificationError(f"Unsupported algorithm: {algo}")
        else:
            sig = signature
        
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            getattr(hashlib, algorithm)
        ).hexdigest()
        
        return hmac.compare_digest(sig, expected_signature)
        
    except Exception as e:
        logger.warning("HMAC signature verification failed", extra={"error": str(e)})
        return False


def verify_webhook_signature_jwt(
    token: str, 
    secret: str,
    max_age_seconds: int = 300
) -> Dict[str, Any]:
    """
    Verify webhook signature using JWT.
    Validates expiration and signature.
    """
    try:
        unverified_payload = jwt.get_unverified_claims(token)
        
        exp = unverified_payload.get("exp")
        if exp:
            current_time = datetime.utcnow().timestamp()
            if current_time > exp:
                raise WebhookVerificationError("JWT token has expired")
            
            if current_time - exp > max_age_seconds:
                raise WebhookVerificationError("JWT token is too old")
        
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        
        return payload
        
    except JWTError as e:
        logger.warning("JWT webhook verification failed", extra={"error": str(e)})
        raise WebhookVerificationError(f"JWT verification failed: {e}")


def verify_webhook_timestamp(timestamp: str, max_age_seconds: int = 300) -> bool:
    """
    Verify webhook timestamp to prevent replay attacks.
    Returns True if timestamp is valid and not too old.
    """
    try:
        if timestamp.isdigit():
            webhook_time = int(timestamp)
        else:
            webhook_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
        
        current_time = datetime.utcnow().timestamp()
        age = current_time - webhook_time
        
        if age < 0:
            logger.warning("Webhook timestamp is in the future", extra={"timestamp": timestamp})
            return False
        
        if age > max_age_seconds:
            logger.warning("Webhook timestamp is too old", extra={
                "timestamp": timestamp,
                "age_seconds": age,
                "max_age_seconds": max_age_seconds
            })
            return False
        
        return True
        
    except (ValueError, TypeError) as e:
        logger.warning("Invalid webhook timestamp format", extra={
            "timestamp": timestamp,
            "error": str(e)
        })
        return False


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for request tracing.
    """
    return str(uuid.uuid4())


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive data from logs.
    """
    sensitive_keys = {
        'password', 'secret', 'token', 'key', 'authorization',
        'client_secret', 'access_token', 'refresh_token'
    }
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized
