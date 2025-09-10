"""
Payout routes for CRUD operations with pagination, authentication, and rate limiting.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import (
    CurrentUser, 
    CorrelationID, 
    get_db,
    AuthServiceDep,
    WebhookSignature
)
from ...schemas.payouts import (
    PayoutCreate,
    PayoutRead,
    PayoutList
)
from ...schemas.webhooks import (
    WebhookRequest,
    WebhookResponse
)
from ...services.payout_service import PayoutService
from ...services.webhook_service import WebhookService
from ...core.logging import get_logger
from ...core.security import sanitize_log_data

logger = get_logger(__name__)

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.post("/", response_model=PayoutRead, status_code=status.HTTP_201_CREATED)
async def create_payout(
    payout_data: PayoutCreate,
    current_user: CurrentUser,
    correlation_id: CorrelationID,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
) -> PayoutRead:
    """
    Create a new payout with idempotency, rate limiting, and retry logic.
    
    """
    try:
        logger.info("Creating payout", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "amount": str(payout_data.amount),
            "currency": payout_data.currency,
            "idempotency_key": idempotency_key
        })
        
        payout_service = PayoutService(db)
        
        payout = await payout_service.create_payout(
            payout_data=payout_data,
            user=current_user,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id
        )
        
        logger.info("Payout created successfully", extra={
            "correlation_id": correlation_id,
            "payout_id": payout.id,
            "user_id": str(current_user.id),
            "status": payout.status,
            "reference": payout.reference
        })
        
        return payout
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Payout creation failed", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "error": str(e),
            "amount": str(payout_data.amount),
            "currency": payout_data.currency
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payout"
        )


@router.get("/", response_model=PayoutList)
async def list_payouts(
    current_user: CurrentUser,
    correlation_id: CorrelationID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page")
) -> PayoutList:
    """
    Get paginated list of payouts for the authenticated user.

    """
    try:
        logger.info("Listing payouts", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "page": page,
            "page_size": page_size
        })
        
        payout_service = PayoutService(db)
        
        payouts = await payout_service.list_payouts(
            user=current_user,
            page=page,
            page_size=page_size,
            correlation_id=correlation_id
        )
        
        logger.info("Payouts listed successfully", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "page": page,
            "page_size": page_size,
            "total": payouts.total,
            "returned_count": len(payouts.items)
        })
        
        return payouts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list payouts", extra={
            "correlation_id": correlation_id,
            "user_id": str(current_user.id),
            "page": page,
            "page_size": page_size,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payouts"
        )


# Webhook endpoint for payment provider notifications
@router.post("/webhooks/payments", response_model=WebhookResponse)
async def receive_payment_webhook(
    webhook_data: WebhookRequest,
    signature_data: WebhookSignature,
    correlation_id: CorrelationID,
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """
    Accept asynchronous webhook updates from payment providers.
    
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
        
        webhook_service = WebhookService(db)
        
        result = await webhook_service.process_webhook_event(
            webhook_data=webhook_data,
            signature_data=signature_data,
            correlation_id=correlation_id
        )
        
        logger.info("Payment webhook processed successfully", extra={
            "correlation_id": correlation_id,
            "event_id": webhook_data.event_id,
            "payment_id": webhook_data.payment_id,
            "processed": result.get("processed", False),
            "payout_id": result.get("payout_id")
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
