"""
Webhook-related test fixtures.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from ...models.payout import Payout, PayoutStatus
from ...schemas.webhooks import WebhookRequest, WebhookEventType


@pytest.fixture
def test_webhook_data() -> WebhookRequest:
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
def test_payout_for_webhook() -> Payout:
    """Create a test payout for webhook processing."""
    payout_id = uuid4()
    payout = Payout(
        id=payout_id,
        reference="PAY_TEST123456789",
        user_id=uuid4(),
        amount=Decimal("100.50"),
        currency="USD",
        status=PayoutStatus.pending,
        idempotency_key="test_idempotency_key",
        retry_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    payout.id = str(payout_id)
    payout.user_id = str(uuid4())
    return payout
