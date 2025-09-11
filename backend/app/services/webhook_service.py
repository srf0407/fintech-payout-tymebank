"""
Webhook service for processing payment provider notifications.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from ..core.logging import get_logger
from ..core.security import sanitize_log_data
from ..models.payout import Payout, PayoutStatus
from ..schemas.webhooks import (
    WebhookRequest,
    WebhookEventType,
    WebhookEvent
)

logger = get_logger(__name__)


class WebhookService:
    """Service for handling webhook operations."""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
    
    async def process_webhook_event(
        self,
        webhook_data: WebhookRequest,
        signature_data: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Process incoming webhook event.
        
        This method:
        - Validates webhook data
        - Finds corresponding payout
        - Updates payout status
        - Handles idempotency
        - Logs all operations
        """
        try:
            logger.info("Processing webhook event", extra={
                "correlation_id": correlation_id,
                "event_type": webhook_data.event_type,
                "event_id": webhook_data.event_id,
                "payment_id": webhook_data.payment_id,
                "reference": webhook_data.reference,
                "status": webhook_data.status
            })
            
            if not self.db:
                # This should not happen as we're passing the session from the callback service
                logger.error("No database session provided to webhook service", extra={
                    "correlation_id": correlation_id
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )
            
            payout = await self._find_payout_by_reference(webhook_data.reference)
            
            if not payout:
                logger.warning("Payout not found for webhook", extra={
                    "correlation_id": correlation_id,
                    "reference": webhook_data.reference,
                    "event_id": webhook_data.event_id
                })
                
                await self._create_webhook_event_record(
                    webhook_data=webhook_data,
                    signature_data=signature_data,
                    correlation_id=correlation_id,
                    payout_id=None
                )
                
                return {
                    "processed": False,
                    "error": "Payout not found",
                    "payout_id": None
                }
            
            if await self._is_duplicate_webhook(webhook_data.event_id, payout.id):
                logger.info("Duplicate webhook ignored", extra={
                    "correlation_id": correlation_id,
                    "event_id": webhook_data.event_id,
                    "payout_id": str(payout.id)
                })
                
                return {
                    "processed": True,
                    "duplicate": True,
                    "payout_id": str(payout.id)
                }
            
            await self._update_payout_from_webhook(
                payout=payout,
                webhook_data=webhook_data,
                correlation_id=correlation_id
            )
            
            await self._create_webhook_event_record(
                webhook_data=webhook_data,
                signature_data=signature_data,
                correlation_id=correlation_id,
                payout_id=payout.id
            )
            
            logger.info("Webhook event processed successfully", extra={
                "correlation_id": correlation_id,
                "event_id": webhook_data.event_id,
                "payout_id": str(payout.id),
                "new_status": webhook_data.status
            })
            
            return {
                "processed": True,
                "payout_id": str(payout.id),
                "status_updated": True
            }
            
        except Exception as e:
            logger.error("Webhook processing failed", extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "event_id": webhook_data.event_id
            })
            
            await self._create_webhook_event_record(
                webhook_data=webhook_data,
                signature_data=signature_data,
                correlation_id=correlation_id,
                payout_id=None,
                error=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook processing failed"
            )
    
    async def _find_payout_by_reference(self, reference: str) -> Optional[Payout]:
        """Find payout by reference."""
        try:
            stmt = select(Payout).where(Payout.reference == reference)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to find payout by reference", extra={
                "reference": reference,
                "error": str(e)
            })
            return None
    
    async def _is_duplicate_webhook(self, event_id: str, payout_id: UUID) -> bool:
        """Check if webhook event is duplicate using existing payout fields."""
        try:
            stmt = select(Payout).where(
                Payout.id == payout_id,
                Payout.last_webhook_event_id == event_id
            )
            result = await self.db.execute(stmt)
            payout = result.scalar_one_or_none()
            
            if payout:
                logger.info("Duplicate webhook detected", extra={
                    "event_id": event_id,
                    "payout_id": str(payout_id),
                    "existing_status": payout.provider_status,
                    "webhook_received_at": payout.webhook_received_at.isoformat() if payout.webhook_received_at else None
                })
                return True
            
            return False
        except Exception as e:
            logger.error("Failed to check duplicate webhook", extra={
                "event_id": event_id,
                "payout_id": str(payout_id),
                "error": str(e)
            })
            # Fail open for safety - if we can't check, allow processing
            return False
    
    async def _update_payout_from_webhook(
        self,
        payout: Payout,
        webhook_data: WebhookRequest,
        correlation_id: str
    ) -> None:
        """Update payout status from webhook data."""
        try:
            status_mapping = {
                "pending": PayoutStatus.pending,
                "processing": PayoutStatus.processing,
                "succeeded": PayoutStatus.succeeded,
                "failed": PayoutStatus.failed,
                "cancelled": PayoutStatus.cancelled
            }
            
            new_status = status_mapping.get(webhook_data.status, PayoutStatus.pending)
            
            payout.status = new_status
            payout.provider_reference = webhook_data.payment_id
            payout.provider_status = webhook_data.status
            payout.webhook_received_at = datetime.utcnow()
            payout.last_webhook_event_id = webhook_data.event_id
            # Only set correlation_id if it's a valid UUID format
            try:
                payout.correlation_id = UUID(correlation_id)
            except ValueError:
                # If correlation_id is not a valid UUID, generate a new one
                payout.correlation_id = uuid4()
                logger.warning("Invalid correlation_id format, generated new UUID", extra={
                    "correlation_id": correlation_id,
                    "payout_id": str(payout.id)
                })
            
            if webhook_data.status == "failed":
                payout.error_code = webhook_data.error_code
                payout.error_message = webhook_data.error_message
            
            if webhook_data.metadata:
                payout.metadata_json = webhook_data.metadata
            
            await self.db.commit()
            await self.db.refresh(payout)
            
            logger.info("Payout updated from webhook", extra={
                "correlation_id": correlation_id,
                "payout_id": str(payout.id),
                "reference": payout.reference,
                "old_status": payout.status,
                "new_status": new_status,
                "provider_reference": webhook_data.payment_id,
                "webhook_event_id": webhook_data.event_id
            })
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Failed to update payout from webhook", extra={
                "correlation_id": correlation_id,
                "payout_id": str(payout.id),
                "error": str(e)
            })
            raise
    
    async def _create_webhook_event_record(
        self,
        webhook_data: WebhookRequest,
        signature_data: Dict[str, Any],
        correlation_id: str,
        payout_id: Optional[UUID],
        error: Optional[str] = None
    ) -> None:
        """Create webhook event record for tracking."""
        try:
            # In a real implementation, you'd have a webhook_events table
            # For now, we'll just log the event
            logger.info("Webhook event recorded", extra={
                "correlation_id": correlation_id,
                "event_id": webhook_data.event_id,
                "event_type": webhook_data.event_type,
                "payout_id": str(payout_id) if payout_id else None,
                "error": error,
                "signature_type": signature_data.get("type")
            })
            
        except Exception as e:
            logger.error("Failed to create webhook event record", extra={
                "correlation_id": correlation_id,
                "error": str(e)
            })
    
