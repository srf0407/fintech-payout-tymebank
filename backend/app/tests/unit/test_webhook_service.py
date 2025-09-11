"""
Unit tests for webhook service business logic.
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

from ...models.payout import Payout, PayoutStatus
from ...schemas.webhooks import WebhookRequest, WebhookEventType
from ...services.webhook_service import WebhookService


class TestWebhookService:
    """Test suite for webhook service business logic."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def test_webhook_data(self) -> WebhookRequest:
        """Create test webhook data."""
        return WebhookRequest(
            event_type=WebhookEventType.PAYMENT_SUCCEEDED,
            event_id="evt_test123",
            timestamp=datetime.utcnow(),
            payment_id="pay_test123",
            reference="PAY_TEST123456789",
            status="succeeded",
            amount=100.50,
            currency="USD"
        )
    
    @pytest.fixture
    def test_payout(self) -> Payout:
        """Create a test payout."""
        return Payout(
            id=uuid4(),
            reference="PAY_TEST123456789",
            user_id=uuid4(),
            amount=Decimal("100.50"),
            currency="USD",
            status=PayoutStatus.pending,
            idempotency_key="test_idempotency_key",
            retry_count=0
        )
    
    @pytest.mark.asyncio
    async def test_webhook_service_processing(
        self,
        mock_db_session,
        test_webhook_data: WebhookRequest,
        test_payout: Payout
    ):
        """Test webhook service processing."""
        webhook_service = WebhookService(mock_db_session)
        
        # Mock the webhook service methods directly
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=test_payout) as mock_find:
            with patch.object(webhook_service, '_is_duplicate_webhook', return_value=False) as mock_duplicate:
                with patch.object(webhook_service, '_update_payout_from_webhook') as mock_update:
                    with patch.object(webhook_service, '_create_webhook_event_record') as mock_record:
                        signature_data = {"type": "hmac_sha256", "verified": True}
                        
                        result = await webhook_service.process_webhook_event(
                            webhook_data=test_webhook_data,
                            signature_data=signature_data,
                            correlation_id="test_correlation_id"
                        )
                        
                        assert result["processed"] is True
                        assert "payout_id" in result
    
    @pytest.mark.asyncio
    async def test_webhook_service_duplicate_detection(
        self,
        mock_db_session,
        test_webhook_data: WebhookRequest,
        test_payout: Payout
    ):
        """Test webhook duplicate detection."""
        webhook_service = WebhookService(mock_db_session)
        
        # Mock duplicate webhook
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=test_payout) as mock_find:
            with patch.object(webhook_service, '_is_duplicate_webhook', return_value=True) as mock_duplicate:
                signature_data = {"type": "hmac_sha256", "verified": True}
                
                result = await webhook_service.process_webhook_event(
                    webhook_data=test_webhook_data,
                    signature_data=signature_data,
                    correlation_id="test_correlation_id"
                )
                
                # The actual implementation returns processed=True for duplicates
                assert result["processed"] is True
                assert result["duplicate"] is True
                assert "payout_id" in result
    
    @pytest.mark.asyncio
    async def test_webhook_idempotency_with_existing_fields(
        self,
        mock_db_session,
        test_webhook_data: WebhookRequest,
        test_payout: Payout
    ):
        """Test webhook idempotency using existing payout fields."""
        webhook_service = WebhookService(mock_db_session)
        
        # Mock payout that already has the same webhook event_id
        test_payout.last_webhook_event_id = test_webhook_data.event_id
        test_payout.webhook_received_at = datetime.utcnow()
        test_payout.provider_status = test_webhook_data.status
        
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=test_payout):
            with patch.object(webhook_service, '_is_duplicate_webhook', return_value=True) as mock_duplicate:
                signature_data = {"type": "hmac_sha256", "verified": True}
                
                result = await webhook_service.process_webhook_event(
                    webhook_data=test_webhook_data,
                    signature_data=signature_data,
                    correlation_id="550e8400-e29b-41d4-a716-446655440000"  # Valid UUID format
                )
                
                # Should detect duplicate and return early
                assert result["processed"] is True
                assert result["duplicate"] is True
                assert "payout_id" in result
                
                # Verify duplicate check was called
                mock_duplicate.assert_called_once_with(test_webhook_data.event_id, test_payout.id)
    
    @pytest.mark.asyncio
    async def test_webhook_idempotency_new_event_id(
        self,
        mock_db_session,
        test_webhook_data: WebhookRequest,
        test_payout: Payout
    ):
        """Test webhook processing with new event_id (not duplicate)."""
        webhook_service = WebhookService(mock_db_session)
        
        # Mock payout with different event_id (not duplicate)
        test_payout.last_webhook_event_id = "different_event_id"
        
        # Mock database query to return None (no duplicate found)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=test_payout):
            with patch.object(webhook_service, '_update_payout_from_webhook') as mock_update:
                with patch.object(webhook_service, '_create_webhook_event_record') as mock_record:
                    signature_data = {"type": "hmac_sha256", "verified": True}
                    
                    result = await webhook_service.process_webhook_event(
                        webhook_data=test_webhook_data,
                        signature_data=signature_data,
                        correlation_id="550e8400-e29b-41d4-a716-446655440000"  # Valid UUID format
                    )
                    
                    # Should process normally (not duplicate)
                    assert result["processed"] is True
                    assert result.get("duplicate", False) is False
                    assert "payout_id" in result
                    
                    # Verify update was called
                    mock_update.assert_called_once()
                    mock_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_webhook_service_payout_not_found(
        self,
        mock_db_session,
        test_webhook_data: WebhookRequest
    ):
        """Test webhook processing when payout not found."""
        webhook_service = WebhookService(mock_db_session)
        
        # Mock payout not found
        with patch.object(webhook_service, '_find_payout_by_reference', return_value=None) as mock_find:
            signature_data = {"type": "hmac_sha256", "verified": True}
            
            result = await webhook_service.process_webhook_event(
                webhook_data=test_webhook_data,
                signature_data=signature_data,
                correlation_id="test_correlation_id"
            )
            
            assert result["processed"] is False
            assert result["error"] == "Payout not found"
            assert result["payout_id"] is None
