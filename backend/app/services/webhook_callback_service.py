"""
Webhook callback service for registering and managing webhook callbacks.
Handles the integration between mock payment provider and webhook endpoints.
"""

import asyncio
import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException, status

from ..core.config import settings
from ..core.logging import get_logger
from ..core.security import generate_correlation_id
from ..services.mock_payment_provider import mock_payment_provider

logger = get_logger(__name__)


class WebhookCallbackService:
    """Service for managing webhook callbacks from mock payment provider."""
    
    def __init__(self):
        # Use the backend URL for webhook callbacks
        # Use 127.0.0.1 instead of localhost to avoid potential DNS issues
        self.webhook_url = f"http://127.0.0.1:8000/webhooks/payments"
        self.webhook_secret = settings.webhook_secret
        self.is_registered = False
    
    def generate_webhook_signature(self, payload: str) -> str:
        """
        Generate HMAC signature for webhook payload.
        
        Args:
            payload: JSON string payload
            
        Returns:
            HMAC signature string
        """
        signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def send_webhook_callback(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Send webhook callback directly to webhook service.
        
        Args:
            webhook_data: Webhook data from mock provider
            
        Returns:
            True if successful, False otherwise
        """
        try:
            correlation_id = webhook_data.get("correlation_id", generate_correlation_id())
            
            # Import webhook service and schemas
            from ..schemas.webhooks import WebhookRequest, WebhookEventType
            from ..services.webhook_service import WebhookService
            from ..db.session import get_db
            
            # Transform webhook data to match WebhookRequest schema
            webhook_request = WebhookRequest(
                event_type=WebhookEventType.PAYMENT_STATUS_CHANGED,
                event_id=f"mock_event_{webhook_data['id']}_{int(datetime.utcnow().timestamp())}",
                payment_id=webhook_data["provider_reference"],
                reference=webhook_data["id"],  # Use payout ID as reference
                status=webhook_data["status"],
                timestamp=datetime.fromisoformat(webhook_data["timestamp"].replace('Z', '+00:00')),
                metadata={
                    "provider": "mock_payment_provider",
                    "correlation_id": correlation_id
                }
            )
            
            # Create signature data
            signature_data = {
                "type": "hmac_sha256",
                "verified": True
            }
            
            logger.info("Processing webhook callback directly", extra={
                "correlation_id": correlation_id,
                "event_id": webhook_request.event_id,
                "status": webhook_data["status"],
                "reference": webhook_data["id"]
            })
            
            # Get database session and process webhook directly
            # Use the dependency injection pattern instead of manual session management
            from ..db.session import SessionLocal
            
            async with SessionLocal() as db_session:
                webhook_service = WebhookService(db_session)
                
                result = await webhook_service.process_webhook_event(
                    webhook_data=webhook_request,
                    signature_data=signature_data,
                    correlation_id=correlation_id
                )
                
                if result.get("processed", False):
                    logger.info("Webhook callback processed successfully", extra={
                        "correlation_id": correlation_id,
                        "event_id": webhook_request.event_id,
                        "payout_id": result.get("payout_id")
                    })
                    return True
                else:
                    logger.warning("Webhook callback not processed", extra={
                        "correlation_id": correlation_id,
                        "event_id": webhook_request.event_id,
                        "error": result.get("error")
                    })
                    return False
                    
        except Exception as e:
            logger.error("Webhook callback failed", extra={
                "correlation_id": webhook_data.get("correlation_id"),
                "error": str(e)
            })
            return False
    
    def register_webhook_callback(self) -> None:
        """
        Register webhook callback with mock payment provider.
        """
        if self.is_registered:
            logger.info("Webhook callback already registered")
            return
        
        async def webhook_callback(webhook_data: Dict[str, Any]) -> None:
            """Webhook callback function for mock payment provider."""
            try:
                logger.info("Mock provider webhook callback triggered", extra={
                    "payout_id": webhook_data.get("id"),
                    "status": webhook_data.get("status"),
                    "provider_reference": webhook_data.get("provider_reference"),
                    "webhook_data": webhook_data
                })
                
                success = await self.send_webhook_callback(webhook_data)
                
                if success:
                    logger.info("Webhook callback completed successfully", extra={
                        "payout_id": webhook_data.get("id"),
                        "status": webhook_data.get("status")
                    })
                else:
                    logger.error("Webhook callback failed", extra={
                        "payout_id": webhook_data.get("id"),
                        "status": webhook_data.get("status")
                    })
                    
            except Exception as e:
                logger.error("Webhook callback error", extra={
                    "payout_id": webhook_data.get("id"),
                    "error": str(e)
                })
        
        # Register the callback with mock payment provider
        mock_payment_provider.add_webhook_callback(webhook_callback)
        self.is_registered = True
        
        logger.info("Webhook callback registered with mock payment provider", extra={
            "webhook_url": self.webhook_url
        })
    
    def unregister_webhook_callback(self) -> None:
        """Unregister webhook callback (for testing purposes)."""
        # Note: The mock provider doesn't have an unregister method
        # This would need to be implemented if needed
        self.is_registered = False
        logger.info("Webhook callback unregistered")


# Global instance
webhook_callback_service = WebhookCallbackService()
