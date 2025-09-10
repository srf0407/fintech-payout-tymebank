"""
Mock payment provider service for simulating third-party payment API behavior.
Simulates realistic payment processing with configurable delays, errors, and webhook events.
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from ..core.logging import get_logger
from ..core.security import generate_correlation_id

logger = get_logger(__name__)


class MockErrorType(str, Enum):
    """Types of errors the mock provider can simulate."""
    SUCCESS = "success"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    TIMEOUT = "timeout"


class MockPaymentProvider:
    """Mock payment provider that simulates realistic third-party API behavior."""
    
    def __init__(self):
        self.base_url = settings.payment_provider_base_url
        self.timeout = settings.payment_provider_timeout
        self._webhook_callbacks: List[callable] = []
        self._processing_delays: Dict[str, float] = {}
        
        # Configuration for error simulation
        self.error_rates = {
            MockErrorType.SUCCESS: 0.85,  # 85% success rate
            MockErrorType.BAD_REQUEST: 0.05,  # 5% bad request
            MockErrorType.UNAUTHORIZED: 0.02,  # 2% unauthorized
            MockErrorType.RATE_LIMITED: 0.03,  # 3% rate limited
            MockErrorType.INTERNAL_ERROR: 0.04,  # 4% internal error
            MockErrorType.TIMEOUT: 0.01,  # 1% timeout
        }
    
    def add_webhook_callback(self, callback: callable):
        """Add a callback function to be called when webhooks are sent."""
        self._webhook_callbacks.append(callback)
    
    def set_processing_delay(self, payout_id: str, delay_seconds: float):
        """Set a specific processing delay for a payout."""
        self._processing_delays[payout_id] = delay_seconds
    
    def _determine_error_type(self) -> MockErrorType:
        """Determine what type of error to simulate based on configured rates."""
        rand = random.random()
        cumulative = 0.0
        
        for error_type, rate in self.error_rates.items():
            cumulative += rate
            if rand <= cumulative:
                return error_type
        
        return MockErrorType.SUCCESS
    
    def _simulate_processing_delay(self, payout_id: str) -> float:
        """Simulate realistic processing delay."""
        if payout_id in self._processing_delays:
            delay = self._processing_delays[payout_id]
        else:
            delay = random.uniform(1.0, 5.0)
        
        return delay
    
    async def create_payout(
        self,
        payout_id: str,
        amount: Decimal,
        currency: str,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate creating a payout with the mock payment provider.
        
        Args:
            payout_id: Unique payout identifier
            amount: Payout amount
            currency: Currency code
            reference: Payout reference
            metadata: Additional metadata
            correlation_id: Correlation ID for logging
            
        Returns:
            Response from mock provider
            
        Raises:
            HTTPException: Simulated API errors
        """
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        logger.info("Mock provider: Creating payout", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "amount": str(amount),
            "currency": currency,
            "reference": reference
        })
        
        delay = self._simulate_processing_delay(payout_id)
        logger.debug("Mock provider: Simulating processing delay", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "delay_seconds": delay
        })
        
        await asyncio.sleep(delay)
        
        error_type = self._determine_error_type()
        
        logger.info("Mock provider: Determined response type", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "error_type": error_type.value
        })
        
        if error_type == MockErrorType.SUCCESS:
            return await self._handle_success_response(
                payout_id, amount, currency, reference, metadata, correlation_id
            )
        else:
            return await self._handle_error_response(error_type, payout_id, correlation_id)
    
    async def _handle_success_response(
        self,
        payout_id: str,
        amount: Decimal,
        currency: str,
        reference: str,
        metadata: Optional[Dict[str, Any]],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Handle successful payout creation."""
        provider_reference = f"mock_ref_{uuid.uuid4().hex[:16]}"
        
        response = {
            "id": payout_id,
            "reference": reference,
            "provider_reference": provider_reference,
            "amount": str(amount),
            "currency": currency,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        logger.info("Mock provider: Payout created successfully", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "provider_reference": provider_reference
        })
        
        webhook_delay = random.uniform(2.0, 10.0)
        asyncio.create_task(
            self._send_webhook_callback(
                payout_id, provider_reference, "succeeded", webhook_delay, correlation_id
            )
        )
        
        return response
    
    async def _handle_error_response(
        self,
        error_type: MockErrorType,
        payout_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Handle error responses from mock provider."""
        error_responses = {
            MockErrorType.BAD_REQUEST: {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "error": "invalid_request",
                "message": "Invalid payout parameters provided"
            },
            MockErrorType.UNAUTHORIZED: {
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "error": "unauthorized",
                "message": "Invalid API credentials"
            },
            MockErrorType.RATE_LIMITED: {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "error": "rate_limited",
                "message": "Too many requests, please retry later"
            },
            MockErrorType.INTERNAL_ERROR: {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "internal_error",
                "message": "Internal server error occurred"
            },
            MockErrorType.TIMEOUT: {
                "status_code": status.HTTP_408_REQUEST_TIMEOUT,
                "error": "timeout",
                "message": "Request timeout"
            }
        }
        
        error_info = error_responses[error_type]
        
        logger.warning("Mock provider: Simulating error response", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "error_type": error_type.value,
            "status_code": error_info["status_code"]
        })
        
        if error_type == MockErrorType.TIMEOUT:
            await asyncio.sleep(self.timeout + 1)
        
        raise HTTPException(
            status_code=error_info["status_code"],
            detail={
                "error": error_info["error"],
                "message": error_info["message"],
                "payout_id": payout_id,
                "correlation_id": correlation_id
            }
        )
    
    async def _send_webhook_callback(
        self,
        payout_id: str,
        provider_reference: str,
        status: str,
        delay_seconds: float,
        correlation_id: str
    ):
        """Send webhook callback after delay."""
        logger.info("Mock provider: Scheduling webhook callback", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "provider_reference": provider_reference,
            "status": status,
            "delay_seconds": delay_seconds
        })
        
        await asyncio.sleep(delay_seconds)
        
        webhook_data = {
            "id": payout_id,
            "provider_reference": provider_reference,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id
        }
        
        logger.info("Mock provider: Sending webhook callback", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "provider_reference": provider_reference,
            "status": status,
            "webhook_data": webhook_data
        })
        
        for callback in self._webhook_callbacks:
            try:
                await callback(webhook_data)
            except Exception as e:
                logger.error("Mock provider: Webhook callback failed", extra={
                    "correlation_id": correlation_id,
                    "payout_id": payout_id,
                    "error": str(e),
                    "callback": callback.__name__
                })
    
    async def get_payout_status(
        self,
        payout_id: str,
        provider_reference: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate getting payout status from mock provider.
        
        Args:
            payout_id: Payout ID
            provider_reference: Provider reference
            correlation_id: Correlation ID for logging
            
        Returns:
            Status response from mock provider
        """
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        logger.info("Mock provider: Getting payout status", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "provider_reference": provider_reference
        })
        
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        statuses = ["processing", "succeeded", "failed"]
        status = random.choice(statuses)
        
        response = {
            "id": payout_id,
            "provider_reference": provider_reference,
            "status": status,
            "checked_at": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id
        }
        
        logger.info("Mock provider: Status retrieved", extra={
            "correlation_id": correlation_id,
            "payout_id": payout_id,
            "provider_reference": provider_reference,
            "status": status
        })
        
        return response
    
    def configure_error_rates(self, error_rates: Dict[MockErrorType, float]):
        """Configure error rates for different error types."""
        total_rate = sum(error_rates.values())
        if abs(total_rate - 1.0) > 0.01:
            raise ValueError(f"Error rates must sum to 1.0, got {total_rate}")
        
        self.error_rates = error_rates
        logger.info("Mock provider: Error rates configured", extra={
            "error_rates": {k.value: v for k, v in error_rates.items()}
        })
    
    def reset_configuration(self):
        """Reset mock provider to default configuration."""
        self.error_rates = {
            MockErrorType.SUCCESS: 0.85,
            MockErrorType.BAD_REQUEST: 0.05,
            MockErrorType.UNAUTHORIZED: 0.02,
            MockErrorType.RATE_LIMITED: 0.03,
            MockErrorType.INTERNAL_ERROR: 0.04,
            MockErrorType.TIMEOUT: 0.01,
        }
        self._processing_delays.clear()
        logger.info("Mock provider: Configuration reset to defaults")


mock_payment_provider = MockPaymentProvider()
