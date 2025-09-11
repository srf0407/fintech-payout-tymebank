"""
Security tests for OAuth 2.0, JWT tokens, and webhook verification.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from ..core.security import (
    generate_oauth_state,
    validate_oauth_state,
    generate_code_verifier,
    generate_code_challenge,
    create_access_token,
    verify_access_token,
    verify_webhook_signature_hmac,
    verify_webhook_signature_jwt,
    verify_webhook_timestamp,
    OAuthStateError,
    WebhookVerificationError
)


class TestOAuthSecurity:
    """Test OAuth 2.0 security mechanisms."""
    
    def test_generate_oauth_state(self):
        """Test OAuth state generation."""
        state = generate_oauth_state()
        
        parts = state.split(':')
        assert len(parts) == 3
        
     
        timestamp = int(parts[0])
        current_time = int(datetime.utcnow().timestamp())
        assert abs(current_time - timestamp) < 5 
        
        assert len(parts[1]) == 32  
        
       
        assert len(parts[2]) == 64  
    
    def test_validate_oauth_state_valid(self):
        """Test valid OAuth state validation."""
        state = generate_oauth_state()
        assert validate_oauth_state(state) is True
    
    def test_pkce_code_verifier_generation(self):
        """Test PKCE code verifier and challenge generation."""
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        
        assert isinstance(code_verifier, str)
        assert len(code_verifier) >= 43  # Minimum length for 32 bytes base64
        assert code_verifier.replace('-', '').replace('_', '').isalnum()
        
        assert code_challenge != code_verifier
        assert len(code_challenge) == 43  # SHA256 hash base64 encoded
    
    def test_validate_oauth_state_invalid_format(self):
        """Test invalid OAuth state format."""
        with pytest.raises(OAuthStateError):
            validate_oauth_state("invalid-state")
    
    def test_validate_oauth_state_invalid_signature(self):
        """Test OAuth state with invalid signature."""
        state = generate_oauth_state()
        parts = state.split(':')
        parts[2] = "invalid_signature"
        corrupted_state = ':'.join(parts)
        
        with pytest.raises(OAuthStateError):
            validate_oauth_state(corrupted_state)
    
    def test_generate_code_verifier(self):
        """Test PKCE code verifier generation."""
        verifier = generate_code_verifier()
        
        assert isinstance(verifier, str)
        assert len(verifier) >= 43
        assert all(c.isalnum() or c in '-_' for c in verifier)
    
    def test_generate_code_challenge(self):
        """Test PKCE code challenge generation."""
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        
        assert isinstance(challenge, str)
        assert len(challenge) == 43 
        assert all(c.isalnum() or c in '-_' for c in challenge)
        
        challenge2 = generate_code_challenge(verifier)
        assert challenge == challenge2


class TestJWTSecurity:
    """Test JWT token security."""
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "google_id": "google123"
        }
        
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        parts = token.split('.')
        assert len(parts) == 3
    
    def test_verify_access_token_valid(self):
        """Test valid JWT token verification."""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "google_id": "google123"
        }
        
        token = create_access_token(data)
        payload = verify_access_token(token)
        
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["google_id"] == "google123"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_verify_access_token_invalid(self):
        """Test invalid JWT token verification."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_access_token_expired(self):
        """Test expired JWT token verification."""
        from fastapi import HTTPException
        
        data = {"sub": "user123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(token)
        
        assert exc_info.value.status_code == 401


class TestWebhookSecurity:
    """Test webhook security mechanisms."""
    
    def test_verify_webhook_signature_hmac_valid(self):
        """Test valid HMAC signature verification."""
        payload = b'{"event": "payment.succeeded"}'
        secret = "test-secret"
        
        import hmac
        import hashlib
        
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_webhook_signature_hmac(payload, f"sha256={signature}", secret)
    
    def test_verify_webhook_signature_hmac_invalid(self):
        """Test invalid HMAC signature verification."""
        payload = b'{"event": "payment.succeeded"}'
        secret = "test-secret"
        invalid_signature = "invalid_signature"
        
        assert not verify_webhook_signature_hmac(payload, f"sha256={invalid_signature}", secret)
    
    def test_verify_webhook_signature_jwt_valid(self):
        """Test valid JWT signature verification."""
        from jose import jwt
        
        payload = {
            "event": "payment.succeeded",
            "exp": int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
        }
        
        secret = "test-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        result = verify_webhook_signature_jwt(token, secret)
        assert result["event"] == "payment.succeeded"
    
    def test_verify_webhook_signature_jwt_expired(self):
        """Test expired JWT signature verification."""
        from jose import jwt
        
        payload = {
            "event": "payment.succeeded",
            "exp": int((datetime.utcnow() - timedelta(minutes=1)).timestamp())
        }
        
        secret = "test-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        with pytest.raises(WebhookVerificationError):
            verify_webhook_signature_jwt(token, secret)
    
    def test_verify_webhook_timestamp_valid(self):
        """Test valid webhook timestamp."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        assert verify_webhook_timestamp(timestamp)
    
    def test_verify_webhook_timestamp_too_old(self):
        """Test webhook timestamp that's too old."""
        old_timestamp = str(int((datetime.utcnow() - timedelta(minutes=10)).timestamp()))
        assert not verify_webhook_timestamp(old_timestamp, max_age_seconds=300)
    
    def test_verify_webhook_timestamp_future(self):
        """Test webhook timestamp in the future."""
        future_timestamp = str(int((datetime.utcnow() + timedelta(minutes=1)).timestamp()))
        assert not verify_webhook_timestamp(future_timestamp)
    
    def test_verify_webhook_timestamp_invalid_format(self):
        """Test invalid webhook timestamp format."""
        assert not verify_webhook_timestamp("invalid-timestamp")


class TestSecurityIntegration:
    """Integration tests for security features."""
    
    @pytest.mark.asyncio
    async def test_oauth_flow_security(self):
        """Test complete OAuth flow security."""
        state = generate_oauth_state()
        code_verifier = generate_code_verifier()
        
        assert validate_oauth_state(state)
        
        code_challenge = generate_code_challenge(code_verifier)
        assert len(code_challenge) == 43
    
    def test_webhook_flow_security(self):
        """Test complete webhook flow security."""
        payload = b'{"event": "payment.succeeded", "payment_id": "pay_123"}'
        secret = "webhook-secret"
        
        import hmac
        import hashlib
        
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_webhook_signature_hmac(payload, f"sha256={signature}", secret)
        
        timestamp = str(int(datetime.utcnow().timestamp()))
        assert verify_webhook_timestamp(timestamp)
    
    def test_jwt_flow_security(self):
        """Test complete JWT flow security."""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "google_id": "google123"
        }
        
        token = create_access_token(user_data)
        
        payload = verify_access_token(token)
        
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["google_id"] == "google123"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
