"""
Payout service for handling payout creation, processing, and status management.
Implements idempotency, retry logic, rate limiting, and integration with mock payment provider.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from ..core.logging import get_logger
from ..core.security import generate_correlation_id
from ..models.payout import Payout, PayoutStatus
from ..models.user import User
from ..schemas.payouts import PayoutCreate, PayoutRead, PayoutList
from ..utils.retry import retry_async, PAYMENT_API_RETRY_CONFIG, RetryError
from .mock_payment_provider import mock_payment_provider
from .rate_limiter import rate_limiter_service, RateLimitExceeded, create_rate_limit_exception

logger = get_logger(__name__)


class PayoutService:
    """Service for handling payout operations with business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_payout(
        self,
        payout_data: PayoutCreate,
        user: User,
        idempotency_key: str,
        correlation_id: Optional[str] = None
    ) -> PayoutRead:
        """
        Create a new payout with idempotency, rate limiting, and retry logic.
        
        Args:
            payout_data: Payout creation data
            user: User creating the payout
            idempotency_key: Idempotency key for duplicate prevention
            correlation_id: Correlation ID for logging
            
        Returns:
            Created payout information
            
        Raises:
            HTTPException: For various error scenarios
        """
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        logger.info("Creating payout", extra={
            "correlation_id": correlation_id,
            "user_id": str(user.id),
            "amount": str(payout_data.amount),
            "currency": payout_data.currency,
            "idempotency_key": idempotency_key
        })
        
        try:
            rate_limit_info = rate_limiter_service.check_payout_rate_limit(
                str(user.id), correlation_id
            )
            logger.debug("Rate limit check passed", extra={
                "correlation_id": correlation_id,
                "user_id": str(user.id),
                "remaining_requests": rate_limit_info["remaining_requests"]
            })
        except RateLimitExceeded as e:
            logger.warning("Rate limit exceeded for payout creation", extra={
                "correlation_id": correlation_id,
                "user_id": str(user.id),
                "retry_after": e.retry_after
            })
            raise create_rate_limit_exception(e.retry_after, correlation_id)
        
        existing_payout = await self._get_payout_by_idempotency_key(idempotency_key)
        if existing_payout:
            logger.info("Payout already exists with idempotency key", extra={
                "correlation_id": correlation_id,
                "payout_id": existing_payout.id,
                "idempotency_key": idempotency_key,
                "status": existing_payout.status
            })
            return PayoutRead.model_validate(existing_payout)
        
        payout = await self._create_payout_in_db(
            payout_data, user, idempotency_key, correlation_id
        )
        
        try:
            await self._process_payout_with_provider(payout, correlation_id)
        except Exception as e:
            logger.error("Failed to process payout with provider", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            await self._update_payout_status(
                payout.id, PayoutStatus.failed, correlation_id,
                error_code="provider_error", error_message=str(e)
            )
        
        await self.db.refresh(payout)
        
        logger.info("Payout created successfully", extra={
            "correlation_id": correlation_id,
            "payout_id": payout.id,
            "status": payout.status,
            "provider_reference": payout.provider_reference
        })
        
        return PayoutRead.model_validate(payout)
    
    async def _get_payout_by_idempotency_key(self, idempotency_key: str) -> Optional[Payout]:
        """Get existing payout by idempotency key."""
        try:
            stmt = select(Payout).where(Payout.idempotency_key == idempotency_key)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get payout by idempotency key", extra={
                "idempotency_key": idempotency_key,
                "error": str(e)
            })
            return None
    
    async def _create_payout_in_db(
        self,
        payout_data: PayoutCreate,
        user: User,
        idempotency_key: str,
        correlation_id: str
    ) -> Payout:
        """Create payout in database within transaction."""
        try:
            reference = f"PAY_{uuid.uuid4().hex[:16].upper()}"
            
            payout = Payout(
                reference=reference,
                user_id=user.id,
                amount=payout_data.amount,
                currency=payout_data.currency,
                status=PayoutStatus.pending,
                idempotency_key=idempotency_key,
                metadata_json=payout_data.metadata_json,
                correlation_id=UUID(correlation_id) if correlation_id else None
            )
            
            self.db.add(payout)
            await self.db.commit()
            await self.db.refresh(payout)
            
            logger.info("Payout created in database", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "reference": payout.reference,
                "status": payout.status
            })
            
            return payout
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error("Database integrity error creating payout", extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "idempotency_key": idempotency_key
            })
            
            if "idempotency_key" in str(e):
                existing_payout = await self._get_payout_by_idempotency_key(idempotency_key)
                if existing_payout:
                    return existing_payout
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payout creation conflict"
            )
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to create payout in database", extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "idempotency_key": idempotency_key
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payout"
            )
    
    async def _process_payout_with_provider(
        self,
        payout: Payout,
        correlation_id: str
    ) -> None:
        """Process payout with mock payment provider using retry logic."""
        logger.info("Processing payout with provider", extra={
            "correlation_id": correlation_id,
            "payout_id": payout.id,
            "amount": str(payout.amount),
            "currency": payout.currency
        })
        
        await self._update_payout_status(
            payout.id, PayoutStatus.processing, correlation_id
        )
        
        try:
            provider_response = await retry_async(
                mock_payment_provider.create_payout,
                payout_id=str(payout.id),
                amount=payout.amount,
                currency=payout.currency,
                reference=payout.reference,
                metadata=payout.metadata_json,
                correlation_id=correlation_id,
                config=PAYMENT_API_RETRY_CONFIG
            )
            
            await self._update_payout_with_provider_response(
                payout.id, provider_response, correlation_id
            )
            
            logger.info("Payout processed successfully with provider", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "provider_reference": provider_response.get("provider_reference"),
                "provider_status": provider_response.get("status")
            })
            
        except RetryError as e:
            logger.error("Payout processing failed after retries", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "retry_attempts": e.attempts,
                "last_error": str(e.last_exception)
            })
            
            await self._update_payout_status(
                payout.id, PayoutStatus.failed, correlation_id,
                error_code="provider_retry_exhausted",
                error_message=f"Provider processing failed after {e.attempts} attempts"
            )
            
        except HTTPException as e:
            logger.error("Payout processing failed with HTTP error", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "status_code": e.status_code,
                "detail": str(e.detail)
            })
            
            error_code = "provider_error"
            if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                error_code = "provider_rate_limited"
            elif e.status_code == status.HTTP_400_BAD_REQUEST:
                error_code = "provider_bad_request"
            elif e.status_code == status.HTTP_401_UNAUTHORIZED:
                error_code = "provider_unauthorized"
            elif e.status_code >= 500:
                error_code = "provider_internal_error"
            
            await self._update_payout_status(
                payout.id, PayoutStatus.failed, correlation_id,
                error_code=error_code,
                error_message=str(e.detail)
            )
    
    async def _update_payout_status(
        self,
        payout_id: UUID,
        status: PayoutStatus,
        correlation_id: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        provider_reference: Optional[str] = None,
        provider_status: Optional[str] = None
    ) -> None:
        """Update payout status in database."""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if error_code:
                update_data["error_code"] = error_code
            if error_message:
                update_data["error_message"] = error_message
            if provider_reference:
                update_data["provider_reference"] = provider_reference
            if provider_status:
                update_data["provider_status"] = provider_status
            
            stmt = update(Payout).where(Payout.id == payout_id).values(**update_data)
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info("Payout status updated", extra={
                "correlation_id": correlation_id,
                "payout_id": payout_id,
                "status": status,
                "error_code": error_code,
                "provider_reference": provider_reference
            })
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update payout status", extra={
                "correlation_id": correlation_id,
                "payout_id": payout_id,
                "status": status,
                "error": str(e)
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update payout status"
            )
    
    async def _update_payout_with_provider_response(
        self,
        payout_id: UUID,
        provider_response: Dict[str, Any],
        correlation_id: str
    ) -> None:
        """Update payout with provider response data."""
        provider_reference = provider_response.get("provider_reference")
        provider_status = provider_response.get("status")
        
        await self._update_payout_status(
            payout_id, PayoutStatus.processing, correlation_id,
            provider_reference=provider_reference,
            provider_status=provider_status
        )
    
    async def get_payout_by_id(
        self,
        payout_id: UUID,
        user: User,
        correlation_id: Optional[str] = None
    ) -> Optional[PayoutRead]:
        """Get payout by ID for a specific user."""
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        try:
            stmt = select(Payout).where(
                Payout.id == payout_id,
                Payout.user_id == user.id
            )
            result = await self.db.execute(stmt)
            payout = result.scalar_one_or_none()
            
            if payout:
                logger.info("Payout retrieved", extra={
                    "correlation_id": correlation_id,
                    "payout_id": payout_id,
                    "user_id": str(user.id),
                    "status": payout.status
                })
                return PayoutRead.model_validate(payout)
            else:
                logger.warning("Payout not found", extra={
                    "correlation_id": correlation_id,
                    "payout_id": payout_id,
                    "user_id": str(user.id)
                })
                return None
                
        except Exception as e:
            logger.error("Failed to get payout by ID", extra={
                "correlation_id": correlation_id,
                "payout_id": payout_id,
                "user_id": str(user.id),
                "error": str(e)
            })
            return None
    
    async def list_payouts(
        self,
        user: User,
        page: int = 1,
        page_size: int = 20,
        correlation_id: Optional[str] = None
    ) -> PayoutList:
        """Get paginated list of payouts for a user."""
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        try:
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
            
            offset = (page - 1) * page_size
            
            count_stmt = select(Payout).where(Payout.user_id == user.id)
            count_result = await self.db.execute(count_stmt)
            total = len(await count_result.scalars().all())
            
            stmt = (
                select(Payout)
                .where(Payout.user_id == user.id)
                .order_by(Payout.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            result = await self.db.execute(stmt)
            payouts = await result.scalars().all()
            
            payout_reads = [PayoutRead.model_validate(payout) for payout in payouts]
            
            logger.info("Payouts listed", extra={
                "correlation_id": correlation_id,
                "user_id": str(user.id),
                "page": page,
                "page_size": page_size,
                "total": total,
                "returned_count": len(payout_reads)
            })
            
            return PayoutList(
                items=payout_reads,
                page=page,
                page_size=page_size,
                total=total
            )
            
        except Exception as e:
            logger.error("Failed to list payouts", extra={
                "correlation_id": correlation_id,
                "user_id": str(user.id),
                "page": page,
                "page_size": page_size,
                "error": str(e)
            })
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve payouts"
            )
    
    async def update_payout_from_webhook(
        self,
        payout_id: UUID,
        provider_reference: str,
        status: str,
        correlation_id: str
    ) -> bool:
        """Update payout status from webhook callback."""
        try:
            stmt = select(Payout).where(
                Payout.provider_reference == provider_reference
            )
            result = await self.db.execute(stmt)
            payout = result.scalar_one_or_none()
            
            if not payout:
                logger.warning("Payout not found for webhook", extra={
                    "correlation_id": correlation_id,
                    "provider_reference": provider_reference,
                    "status": status
                })
                return False
            
            payout_status = PayoutStatus.processing
            if status == "succeeded":
                payout_status = PayoutStatus.succeeded
            elif status == "failed":
                payout_status = PayoutStatus.failed
            elif status == "cancelled":
                payout_status = PayoutStatus.cancelled
            
            await self._update_payout_status(
                payout.id, payout_status, correlation_id,
                provider_status=status,
                provider_reference=provider_reference
            )
            
            logger.info("Payout updated from webhook", extra={
                "correlation_id": correlation_id,
                "payout_id": payout.id,
                "provider_reference": provider_reference,
                "status": payout_status,
                "provider_status": status
            })
            
            return True
            
        except Exception as e:
            logger.error("Failed to update payout from webhook", extra={
                "correlation_id": correlation_id,
                "provider_reference": provider_reference,
                "status": status,
                "error": str(e)
            })
            return False
