"""
Authentication-related test fixtures.
"""

import pytest
from uuid import uuid4

from ...models.user import User


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
def test_user_data() -> dict:
    """Create test user data for JWT tokens."""
    return {
        "sub": "user123",
        "email": "test@example.com",
        "google_id": "google123",
        "name": "Test User"
    }
