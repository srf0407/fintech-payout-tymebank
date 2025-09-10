"""
Test configuration and fixtures for all tests.
"""

import os
import pytest
import asyncio
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

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


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for tests."""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.database_url = "sqlite+aiosqlite:///:memory:"
        mock_settings.secret_key = "test-secret-key-for-testing-minimum-32-characters-long"
        mock_settings.google_client_id = "test-client-id.apps.googleusercontent.com"
        mock_settings.google_client_secret = "test-client-secret"
        mock_settings.webhook_secret = "test-webhook-secret-for-testing-minimum-32-characters"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.webhook_timeout_seconds = 300
        mock_settings.rate_limit_per_minute = 10
        mock_settings.payment_provider_base_url = "http://localhost:8000/mock-provider"
        mock_settings.payment_provider_timeout = 30
        mock_settings.cors_allow_origins = ["http://localhost:3000"]
        mock_settings.app_name = "Fintech Payouts API Test"
        mock_settings.debug = False
        mock_settings.log_level = "INFO"
        yield mock_settings


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    from ..db.session import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create database session for tests."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for anyio."""
    return "asyncio"
