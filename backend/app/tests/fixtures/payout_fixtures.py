"""
Payout-related test fixtures.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime

from ...models.user import User
from ...models.payout import Payout, PayoutStatus
from ...schemas.payouts import PayoutCreate, PayoutRead


@pytest.fixture
def test_user() -> User:
    """Create a test user."""
    return User(
        id=uuid4(),
        google_id="test_google_id_123",
        email="test@example.com",
        name="Test User",
        picture_url="https://example.com/picture.jpg"
    )


@pytest.fixture
def test_payout_data() -> PayoutCreate:
    """Create test payout data."""
    return PayoutCreate(
        amount=Decimal("100.50"),
        currency="USD",
        metadata_json={"description": "Test payout", "category": "test"}
    )


@pytest.fixture
def test_payout(test_user: User) -> Payout:
    """Create a test payout."""
    payout_id = uuid4()
    payout = Payout(
        id=payout_id,
        reference="PAY_TEST123456789",
        user_id=test_user.id,
        amount=Decimal("100.50"),
        currency="USD",
        status=PayoutStatus.pending,
        idempotency_key="test_idempotency_key",
        metadata_json={"description": "Test payout"},
        retry_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    payout.id = str(payout_id)
    payout.user_id = str(test_user.id)
    return payout


@pytest.fixture
def test_payout_read(test_payout: Payout) -> PayoutRead:
    """Create a test payout read object."""
    return PayoutRead.model_validate(test_payout)
