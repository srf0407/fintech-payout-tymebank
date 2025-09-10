"""
Simple test script to verify business logic components work.
This runs without pytest to avoid async configuration issues.
"""

import pytest
import asyncio
import sys
import os
from decimal import Decimal
from uuid import uuid4

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.rate_limiter import SlidingWindowRateLimiter, RateLimitExceeded
from app.services.mock_payment_provider import MockPaymentProvider, MockErrorType
from app.utils.retry import retry_async, RetryConfig, RetryError
from app.core.security import generate_correlation_id
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_rate_limiter():
    """Test rate limiter functionality."""
    print("🧪 Testing Rate Limiter...")
    
    limiter = SlidingWindowRateLimiter(window_size_seconds=60, max_requests=3)
    user_id = "test_user"
    
    for i in range(3):
        result = limiter.check_rate_limit(user_id)
        print(f"  ✅ Request {i+1}: {result['remaining_requests']} remaining")

    try:
        limiter.check_rate_limit(user_id)
        print("  ❌ Rate limit should have been exceeded!")
        return False
    except RateLimitExceeded as e:
        print(f"  ✅ Rate limit exceeded as expected: {e.retry_after}s")
    
    print("  ✅ Rate limiter tests passed!\n")
    return True


@pytest.mark.asyncio
async def test_mock_payment_provider():
    """Test mock payment provider functionality."""
    print("🧪 Testing Mock Payment Provider...")
    
    provider = MockPaymentProvider()
    provider.configure_error_rates({
        MockErrorType.SUCCESS: 1.0,
        MockErrorType.BAD_REQUEST: 0.0,
        MockErrorType.UNAUTHORIZED: 0.0,
        MockErrorType.RATE_LIMITED: 0.0,
        MockErrorType.INTERNAL_ERROR: 0.0,
        MockErrorType.TIMEOUT: 0.0,
    })
    
    payout_id = str(uuid4())
    correlation_id = generate_correlation_id()
    
    try:
        result = await provider.create_payout(
            payout_id=payout_id,
            amount=Decimal("100.00"),
            currency="USD",
            reference="TEST_REF",
            correlation_id=correlation_id
        )
        
        print(f"  ✅ Payout created: {result['id']}")
        print(f"  ✅ Provider reference: {result['provider_reference']}")
        print(f"  ✅ Status: {result['status']}")
        
        print("  ✅ Mock payment provider tests passed!\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Mock provider test failed: {e}")
        return False


@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry logic functionality."""
    print("🧪 Testing Retry Logic...")
    
    call_count = 0
    
    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await retry_async(success_func, config=RetryConfig(max_retries=3))
    print(f"  ✅ Success function: {result} (calls: {call_count})")
    
    call_count = 0
    
    async def retry_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise HTTPException(status_code=500, detail="Internal error")
        return "success"
    
    result = await retry_async(retry_func, config=RetryConfig(max_retries=3))
    print(f"  ✅ Retry function: {result} (calls: {call_count})")
    
    call_count = 0
    
    async def fail_func():
        nonlocal call_count
        call_count += 1
        raise HTTPException(status_code=500, detail="Internal error")
    
    try:
        await retry_async(fail_func, config=RetryConfig(max_retries=2))
        print("  ❌ Should have failed!")
        return False
    except RetryError as e:
        print(f"  ✅ Retry exhausted as expected: {e.attempts} attempts")
    
    print("  ✅ Retry logic tests passed!\n")
    return True


@pytest.mark.asyncio
async def test_error_simulation():
    """Test error simulation in mock provider."""
    print("🧪 Testing Error Simulation...")
    
    provider = MockPaymentProvider()
    provider.configure_error_rates({
        MockErrorType.SUCCESS: 0.0,
        MockErrorType.BAD_REQUEST: 1.0,  # 100% bad request
        MockErrorType.UNAUTHORIZED: 0.0,
        MockErrorType.RATE_LIMITED: 0.0,
        MockErrorType.INTERNAL_ERROR: 0.0,
        MockErrorType.TIMEOUT: 0.0,
    })
    
    payout_id = str(uuid4())
    correlation_id = generate_correlation_id()
    
    try:
        await provider.create_payout(
            payout_id=payout_id,
            amount=Decimal("100.00"),
            currency="USD",
            reference="TEST_REF",
            correlation_id=correlation_id
        )
        print("  ❌ Should have failed!")
        return False
    except HTTPException as e:
        print(f"  ✅ Error simulation worked: {e.status_code} - {e.detail}")
    
    print("  ✅ Error simulation tests passed!\n")
    return True


async def main():
    """Run all tests."""
    print("🚀 Running Business Logic Tests\n")
    
    tests = [
        test_rate_limiter,
        test_mock_payment_provider,
        test_retry_logic,
        test_error_simulation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All business logic components are working correctly!")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
