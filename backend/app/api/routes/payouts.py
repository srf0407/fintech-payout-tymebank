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
    get_db
)
from ...schemas.payouts import (
    PayoutCreate,
    PayoutRead,
    PayoutList
)
from ...services.payout_service import PayoutService
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


