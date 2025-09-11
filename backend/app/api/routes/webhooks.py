"""
Webhook routes for payment provider notifications.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse

from ..deps import WebhookSignature, CorrelationID, WebhookServiceDep
from ...schemas.webhooks import (
    WebhookRequest,
    WebhookResponse
)
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payments", response_model=WebhookResponse)
async def receive_payment_webhook(
    request: Request,
    webhook_data: WebhookRequest,
    signature_data: WebhookSignature,
    correlation_id: CorrelationID,
    webhook_service: WebhookServiceDep
) -> WebhookResponse:
    """
    Receive and process payment webhook notifications.
    
    This endpoint:
    - Verifies webhook signature (HMAC or JWT)
    - Validates webhook timestamp to prevent replay attacks
    - Processes webhook event
    - Returns acknowledgment response
    
    Security features:
    - HMAC SHA256/SHA1 signature verification
    - JWT signature verification
    - Timestamp validation (replay attack protection)
    - Idempotency handling
    - Structured logging with correlation IDs
    """
    try:
        logger.info("Payment webhook received", extra={
            "correlation_id": correlation_id,
            "event_type": webhook_data.event_type,
            "event_id": webhook_data.event_id,
            "payment_id": webhook_data.payment_id,
            "reference": webhook_data.reference,
            "status": webhook_data.status,
            "signature_type": signature_data.get("type"),
            "timestamp": webhook_data.timestamp.isoformat()
        })
        
        result = await webhook_service.process_webhook_event(
            webhook_data=webhook_data,
            signature_data=signature_data,
            correlation_id=correlation_id
        )
        
        logger.info("Payment webhook processed successfully", extra={
            "correlation_id": correlation_id,
            "event_id": webhook_data.event_id,
            "payment_id": webhook_data.payment_id,
            "processed": result.get("processed", False)
        })
        
        return WebhookResponse(
            success=True,
            message="Webhook processed successfully",
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook processing failed", extra={
            "correlation_id": correlation_id,
            "error": str(e),
            "event_id": webhook_data.event_id if webhook_data else None
        })
        
        return WebhookResponse(
            success=False,
            message="Webhook processing failed",
            correlation_id=correlation_id
        )








