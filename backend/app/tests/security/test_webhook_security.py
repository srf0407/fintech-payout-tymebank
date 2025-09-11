"""
Security tests for webhook signature and timestamp verification.
Tests the two required minimal test scenarios:
- Webhook signature verification
- Webhook timestamp verification (reject if too old)
"""

import pytest
from datetime import datetime, timedelta
import hmac
import hashlib

from ...core.security import (
    verify_webhook_signature_hmac,
    verify_webhook_signature_jwt,
    verify_webhook_timestamp,
    WebhookVerificationError
)


class TestWebhookSecurity:
    """Test webhook security mechanisms - REQUIRED MINIMAL TESTS."""
    
    def test_verify_webhook_signature_hmac_valid(self):
        """Test valid HMAC signature verification - REQUIRED TEST."""
        payload = b'{"event": "payment.succeeded", "payment_id": "pay_123"}'
        secret = "test-webhook-secret"
        
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_webhook_signature_hmac(payload, f"sha256={signature}", secret)
    
    def test_verify_webhook_signature_hmac_invalid(self):
        """Test invalid HMAC signature verification."""
        payload = b'{"event": "payment.succeeded"}'
        secret = "test-webhook-secret"
        invalid_signature = "invalid_signature"
        
        assert not verify_webhook_signature_hmac(payload, f"sha256={invalid_signature}", secret)
    
    def test_verify_webhook_signature_jwt_valid(self):
        """Test valid JWT signature verification."""
        from jose import jwt
        
        payload = {
            "event": "payment.succeeded",
            "exp": int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
        }
        
        secret = "test-webhook-secret"
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
        
        secret = "test-webhook-secret"
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        with pytest.raises(WebhookVerificationError):
            verify_webhook_signature_jwt(token, secret)
    
    def test_verify_webhook_timestamp_valid(self):
        """Test valid webhook timestamp - REQUIRED TEST."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        assert verify_webhook_timestamp(timestamp)
    
    def test_verify_webhook_timestamp_too_old(self):
        """Test webhook timestamp that's too old - REQUIRED TEST."""
        old_timestamp = str(int((datetime.utcnow() - timedelta(minutes=10)).timestamp()))
        assert not verify_webhook_timestamp(old_timestamp, max_age_seconds=300)
    
    def test_verify_webhook_timestamp_future(self):
        """Test webhook timestamp in the future."""
        future_timestamp = str(int((datetime.utcnow() + timedelta(minutes=1)).timestamp()))
        assert not verify_webhook_timestamp(future_timestamp)
    
    def test_verify_webhook_timestamp_invalid_format(self):
        """Test invalid webhook timestamp format."""
        assert not verify_webhook_timestamp("invalid-timestamp")
    
    def test_webhook_security_integration(self):
        """Test complete webhook security flow - REQUIRED INTEGRATION TEST."""
        payload = b'{"event": "payment.succeeded", "payment_id": "pay_123"}'
        secret = "webhook-secret"
        
        # Test signature verification
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert verify_webhook_signature_hmac(payload, f"sha256={signature}", secret)
        
        # Test timestamp verification
        timestamp = str(int(datetime.utcnow().timestamp()))
        assert verify_webhook_timestamp(timestamp)
        
        # Test old timestamp rejection
        old_timestamp = str(int((datetime.utcnow() - timedelta(minutes=10)).timestamp()))
        assert not verify_webhook_timestamp(old_timestamp, max_age_seconds=300)
