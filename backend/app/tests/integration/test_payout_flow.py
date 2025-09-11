"""
Integration tests for complete payout flow.
Tests end-to-end payout creation and processing.
"""

import pytest
import os
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from datetime import datetime

# Set up environment variables before any imports
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SECRET_KEY": "test-secret-key-for-testing-minimum-32-characters-long",
    "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "WEBHOOK_SECRET": "test-webhook-secret-for-testing-minimum-32-characters",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "WEBHOOK_TIMEOUT_SECONDS": "300",
    "RATE_LIMIT_PER_MINUTE": "10",
    "PAYMENT_PROVIDER_BASE_URL": "http://localhost:8000/mock-provider",
    "PAYMENT_PROVIDER_TIMEOUT": "30",
    "CORS_ALLOW_ORIGINS": '["http://localhost:3000"]',
    "APP_NAME": "Fintech Payouts API Test",
    "DEBUG": "false",
    "LOG_LEVEL": "INFO"
})

from ...models.user import User
from ...models.payout import Payout, PayoutStatus
from ...schemas.payouts import PayoutCreate
from ...services.payout_service import PayoutService
from ...services.webhook_service import WebhookService
from ...schemas.webhooks import WebhookRequest, WebhookEventType


class TestPayoutFlow:
    """Integration tests for complete payout flow."""
    
    @pytest.fixture
    def test_user(self) -> User:
        """Create a test user."""
        return User(
            id=uuid4(),
            google_id="test_google_id_123",
            email="test@example.com",
            name="Test User",
            picture_url="https://example.com/picture.jpg"
        )
    
    @pytest.fixture
    def test_payout_data(self) -> PayoutCreate:
        """Create test payout data."""
        return PayoutCreate(
            amount=Decimal("100.50"),
            currency="USD",
            metadata_json={"description": "Test payout", "category": "test"}
        )
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_complete_payout_flow(
        self,
        test_user: User,
        test_payout_data: PayoutCreate,
        mock_db_session
    ):
        """Test complete payout flow from creation to webhook processing."""
        payout_service = PayoutService(mock_db_session)
        webhook_service = WebhookService(mock_db_session)
        
        # Mock successful payout creation
        payout_id = uuid4()
        created_payout = Payout(
            id=payout_id,
            reference="PAY_TEST123456789",
            user_id=test_user.id,
            amount=test_payout_data.amount,
            currency=test_payout_data.currency,
            status=PayoutStatus.processing,
            idempotency_key="test_idempotency_key",
            provider_reference="mock_ref_123456789",
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        created_payout.id = str(payout_id)
        created_payout.user_id = str(test_user.id)
        
        # Mock payout creation
        with patch.object(payout_service, '_get_payout_by_idempotency_key', return_value=None):
            with patch.object(payout_service, '_create_payout_in_db', return_value=created_payout):
                with patch.object(payout_service, '_process_payout_with_provider'):
                    with patch("app.services.payout_service.rate_limiter_service.check_payout_rate_limit") as mock_rate_limit:
                        mock_rate_limit.return_value = {"remaining_requests": 5}
                        
                        # Create payout
                        result = await payout_service.create_payout(
                            payout_data=test_payout_data,
                            user=test_user,
                            idempotency_key="test_idempotency_key",
                            correlation_id="test_correlation_id"
                        )
                        
                        assert result.status == PayoutStatus.processing
                        assert result.provider_reference == "mock_ref_123456789"
        
        # Mock webhook processing
        webhook_data = WebhookRequest(
            event_type=WebhookEventType.PAYMENT_SUCCEEDED,
            event_id="evt_test123",
            timestamp=datetime.utcnow(),
            payment_id="pay_test123",
            reference="PAY_TEST123456789",
            status="succeeded",
            amount=100.50,
            currency="USD"
        )
        
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=created_payout):
            with patch.object(webhook_service, '_is_duplicate_webhook', return_value=False):
                with patch.object(webhook_service, '_update_payout_from_webhook'):
                    with patch.object(webhook_service, '_create_webhook_event_record'):
                        signature_data = {"type": "hmac_sha256", "verified": True}
                        
                        webhook_result = await webhook_service.process_webhook_event(
                            webhook_data=webhook_data,
                            signature_data=signature_data,
                            correlation_id="test_correlation_id"
                        )
                        
                        assert webhook_result["processed"] is True
                        assert "payout_id" in webhook_result
    
    @pytest.mark.asyncio
    async def test_webhook_idempotency_integration(
        self,
        test_user: User,
        test_payout_data: PayoutCreate,
        mock_db_session
    ):
        """Test webhook idempotency in integration flow."""
        webhook_service = WebhookService(mock_db_session)
        
        # Create a payout that has already been processed
        payout_id = uuid4()
        processed_payout = Payout(
            id=payout_id,
            reference="PAY_TEST123456789",
            user_id=test_user.id,
            amount=test_payout_data.amount,
            currency=test_payout_data.currency,
            status=PayoutStatus.succeeded,
            idempotency_key="test_idempotency_key",
            provider_reference="mock_ref_123456789",
            provider_status="succeeded",
            last_webhook_event_id="evt_already_processed",
            webhook_received_at=datetime.utcnow(),
            retry_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        processed_payout.id = str(payout_id)
        processed_payout.user_id = str(test_user.id)
        
        # Create webhook data with the same event_id that was already processed
        webhook_data = WebhookRequest(
            event_type=WebhookEventType.PAYMENT_SUCCEEDED,
            event_id="evt_already_processed",  # Same event_id as already processed
            timestamp=datetime.utcnow(),
            payment_id="pay_test123",
            reference="PAY_TEST123456789",
            status="succeeded",
            amount=100.50,
            currency="USD"
        )
        
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=processed_payout):
            with patch.object(webhook_service, '_is_duplicate_webhook', return_value=True) as mock_duplicate:
                signature_data = {"type": "hmac_sha256", "verified": True}
                
                # First webhook processing (should be duplicate)
                result1 = await webhook_service.process_webhook_event(
                    webhook_data=webhook_data,
                    signature_data=signature_data,
                    correlation_id="550e8400-e29b-41d4-a716-446655440000"  # Valid UUID format
                )
                
                # Second webhook processing (should also be duplicate)
                result2 = await webhook_service.process_webhook_event(
                    webhook_data=webhook_data,
                    signature_data=signature_data,
                    correlation_id="550e8400-e29b-41d4-a716-446655440001"  # Valid UUID format
                )
                
                # Both should be detected as duplicates
                assert result1["processed"] is True
                assert result1["duplicate"] is True
                assert result2["processed"] is True
                assert result2["duplicate"] is True
                
                # Both should return the same payout_id
                assert result1["payout_id"] == result2["payout_id"]
                
                # Verify duplicate check was called twice
                assert mock_duplicate.call_count == 2
    
    @pytest.mark.asyncio
    async def test_payout_flow_with_retry(
        self,
        test_user: User,
        test_payout_data: PayoutCreate,
        mock_db_session
    ):
        """Test payout flow with retry logic."""
        payout_service = PayoutService(mock_db_session)
        
        # Mock payout creation with retry
        payout_id = uuid4()
        created_payout = Payout(
            id=payout_id,
            reference="PAY_TEST123456789",
            user_id=test_user.id,
            amount=test_payout_data.amount,
            currency=test_payout_data.currency,
            status=PayoutStatus.failed,
            idempotency_key="test_idempotency_key",
            error_code="provider_retry_exhausted",
            error_message="Provider processing failed after 5 attempts",
            retry_count=5,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        created_payout.id = str(payout_id)
        created_payout.user_id = str(test_user.id)
        
        # Mock payout creation with retry failure
        with patch.object(payout_service, '_get_payout_by_idempotency_key', return_value=None):
            with patch.object(payout_service, '_create_payout_in_db', return_value=created_payout):
                with patch.object(payout_service, '_process_payout_with_provider') as mock_process:
                    # Mock retry failure
                    from app.utils.retry import RetryError
                    mock_process.side_effect = RetryError("Retry exhausted", Exception("Provider error"), 5)
                    
                    with patch("app.services.payout_service.rate_limiter_service.check_payout_rate_limit") as mock_rate_limit:
                        mock_rate_limit.return_value = {"remaining_requests": 5}
                        
                        # Create payout
                        result = await payout_service.create_payout(
                            payout_data=test_payout_data,
                            user=test_user,
                            idempotency_key="test_idempotency_key",
                            correlation_id="test_correlation_id"
                        )
                        
                        assert result.status == PayoutStatus.failed
                        assert result.error_code == "provider_retry_exhausted"
                        assert result.retry_count == 5
