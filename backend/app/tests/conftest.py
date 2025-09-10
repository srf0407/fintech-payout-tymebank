"""
Test configuration and fixtures for security tests.
"""

import os
import pytest
from unittest.mock import patch

# Set test environment variables before importing any modules
os.environ.update({
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test_db",
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
        mock_settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
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
