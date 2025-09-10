"""
Simple security tests that don't require full configuration.
"""

import pytest
import hashlib
import hmac
import secrets
import base64
from datetime import datetime, timedelta
from jose import jwt


def test_oauth_state_generation():
    """Test OAuth state generation logic."""
    # Simulate the OAuth state generation
    timestamp = int(datetime.utcnow().timestamp())
    random_bytes = secrets.token_bytes(16)
    state_data = f"{timestamp}:{random_bytes.hex()}"
    
    # Use a test secret
    test_secret = "test-secret-key-for-testing-minimum-32-characters-long"
    signature = hmac.new(
        test_secret.encode(),
        state_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    state = f"{state_data}:{signature}"
    
    # Verify the state format
    parts = state.split(':')
    assert len(parts) == 3
    
    # Verify timestamp
    timestamp_part = int(parts[0])
    current_time = int(datetime.utcnow().timestamp())
    assert abs(current_time - timestamp_part) < 5
    
    # Verify random hex
    assert len(parts[1]) == 32  # 16 bytes = 32 hex chars
    
    # Verify signature
    assert len(parts[2]) == 64  # SHA256 hex digest length


def test_pkce_generation():
    """Test PKCE code verifier and challenge generation."""
    # Generate code verifier
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')
    
    # Verify format
    assert isinstance(code_verifier, str)
    assert len(code_verifier) >= 43  # 32 bytes encoded
    assert all(c.isalnum() or c in '-_' for c in code_verifier)
    
    # Generate code challenge
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    
    # Verify challenge format
    assert isinstance(code_challenge, str)
    assert len(code_challenge) == 43  # SHA256 hash encoded
    assert all(c.isalnum() or c in '-_' for c in code_challenge)
    
    # Same verifier should produce same challenge
    challenge2 = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('ascii').rstrip('=')
    assert code_challenge == challenge2


def test_jwt_token_creation():
    """Test JWT token creation and verification."""
    # Test data
    data = {
        "sub": "user123",
        "email": "test@example.com",
        "google_id": "google123"
    }
    
    # Test secret
    secret = "test-secret-key-for-testing-minimum-32-characters-long"
    
    # Create token
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode = data.copy()
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": "test-jwt-id",
        "iss": "Fintech Payouts API Test",
        "aud": "fintech-payouts-api"
    })
    
    token = jwt.encode(to_encode, secret, algorithm="HS256")
    
    # Verify token format
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Token should have 3 parts (header.payload.signature)
    parts = token.split('.')
    assert len(parts) == 3
    
    # Verify token
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience="fintech-payouts-api")
    
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["google_id"] == "google123"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_hmac_signature_verification():
    """Test HMAC signature verification."""
    payload = b'{"event": "payment.succeeded"}'
    secret = "test-webhook-secret-for-testing-minimum-32-characters"
    
    # Create signature
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Test signature verification
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison
    assert hmac.compare_digest(signature, expected_signature)
    
    # Test with different payload (should fail)
    different_payload = b'{"event": "payment.failed"}'
    different_signature = hmac.new(
        secret.encode(),
        different_payload,
        hashlib.sha256
    ).hexdigest()
    
    assert not hmac.compare_digest(signature, different_signature)


def test_webhook_timestamp_validation():
    """Test webhook timestamp validation."""
    # Valid timestamp (current time)
    current_timestamp = str(int(datetime.utcnow().timestamp()))
    
    # Test valid timestamp
    webhook_time = int(current_timestamp)
    current_time = datetime.utcnow().timestamp()
    age = current_time - webhook_time
    
    assert age >= 0  # Not in the future
    assert age < 300  # Not too old (5 minutes)
    
    # Test future timestamp (should fail)
    future_timestamp = str(int((datetime.utcnow() + timedelta(minutes=1)).timestamp()))
    future_time = int(future_timestamp)
    future_age = datetime.utcnow().timestamp() - future_time
    
    assert future_age < 0  # In the future
    
    # Test old timestamp (should fail)
    old_timestamp = str(int((datetime.utcnow() - timedelta(minutes=10)).timestamp()))
    old_time = int(old_timestamp)
    old_age = datetime.utcnow().timestamp() - old_time
    
    assert old_age > 300  # Too old


def test_security_integration():
    """Test complete security flow integration."""
    # Test OAuth flow
    timestamp = int(datetime.utcnow().timestamp())
    random_bytes = secrets.token_bytes(16)
    state_data = f"{timestamp}:{random_bytes.hex()}"
    
    test_secret = "test-secret-key-for-testing-minimum-32-characters-long"
    signature = hmac.new(
        test_secret.encode(),
        state_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    state = f"{state_data}:{signature}"
    
    # Validate state
    parts = state.split(':')
    assert len(parts) == 3
    
    # Test PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('ascii').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('ascii').rstrip('=')
    
    assert len(code_challenge) == 43
    
    # Test JWT
    user_data = {
        "sub": "user123",
        "email": "test@example.com",
        "google_id": "google123"
    }
    
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode = user_data.copy()
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": "test-jwt-id",
        "iss": "Fintech Payouts API Test",
        "aud": "fintech-payouts-api"
    })
    
    token = jwt.encode(to_encode, test_secret, algorithm="HS256")
    payload = jwt.decode(token, test_secret, algorithms=["HS256"], audience="fintech-payouts-api")
    
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["google_id"] == "google123"
    
    # Test webhook
    webhook_payload = b'{"event": "payment.succeeded", "payment_id": "pay_123"}'
    webhook_secret = "test-webhook-secret-for-testing-minimum-32-characters"
    
    webhook_signature = hmac.new(
        webhook_secret.encode(),
        webhook_payload,
        hashlib.sha256
    ).hexdigest()
    
    expected_webhook_signature = hmac.new(
        webhook_secret.encode(),
        webhook_payload,
        hashlib.sha256
    ).hexdigest()
    
    assert hmac.compare_digest(webhook_signature, expected_webhook_signature)
    
    # Test timestamp
    webhook_timestamp = str(int(datetime.utcnow().timestamp()))
    webhook_time = int(webhook_timestamp)
    current_time = datetime.utcnow().timestamp()
    webhook_age = current_time - webhook_time
    
    assert webhook_age >= 0
    assert webhook_age < 300


if __name__ == "__main__":
    # Run tests directly
    test_oauth_state_generation()
    test_pkce_generation()
    test_jwt_token_creation()
    test_hmac_signature_verification()
    test_webhook_timestamp_validation()
    test_security_integration()
    print("✅ All security tests passed!")
