"""
Webhook routes for payment provider notifications.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse

from ..deps import WebhookSignature, CorrelationID, WebhookServiceDep
from ...schemas.webhooks import (
    WebhookRequest,
    WebhookResponse,
    WebhookErrorResponse,
    WebhookEventType,
    WebhookHealthCheck,
    WebhookStats
)
from ...services.webhook_service import WebhookService
from ...core.logging import get_logger
from ...core.security import sanitize_log_data

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


@router.post("/test", response_model=WebhookResponse)
async def test_webhook(
    request: Request,
    test_data: Dict[str, Any],
    signature_data: WebhookSignature,
    correlation_id: CorrelationID
) -> WebhookResponse:
    """
    Test webhook endpoint for signature verification testing.
    
    This endpoint:
    - Verifies webhook signature
    - Returns test response
    - Useful for webhook integration testing
    """
    try:
        logger.info("Test webhook received", extra={
            "correlation_id": correlation_id,
            "signature_type": signature_data.get("type"),
            "test_data": sanitize_log_data(test_data)
        })
        
        return WebhookResponse(
            success=True,
            message="Test webhook received and verified",
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error("Test webhook failed", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        
        return WebhookResponse(
            success=False,
            message="Test webhook failed",
            correlation_id=correlation_id
        )


@router.get("/health", response_model=WebhookHealthCheck)
async def webhook_health_check(
    correlation_id: CorrelationID,
    webhook_service: WebhookServiceDep
) -> WebhookHealthCheck:
    """
    Webhook system health check.
    
    This endpoint:
    - Checks webhook system components
    - Returns health status and statistics
    - Useful for monitoring and alerting
    """
    try:
        logger.info("Webhook health check requested", extra={
            "correlation_id": correlation_id
        })
        
        stats = await webhook_service.get_webhook_stats()
        
        health_status = "healthy"
        issues = []
        
        if stats.success_rate_24h < 0.95: 
            health_status = "degraded"
            issues.append("Low success rate in last 24 hours")
        
        if stats.pending_deliveries > 100:  
            health_status = "degraded"
            issues.append("High number of pending deliveries")
        
        if stats.failed_deliveries > stats.successful_deliveries: 
            health_status = "unhealthy"
            issues.append("More failed deliveries than successful ones")
        
        health_check = WebhookHealthCheck(
            status=health_status,
            database="healthy",
            signature_verification="healthy",
            event_processing="healthy",
            stats=stats,
            issues=issues
        )
        
        logger.info("Webhook health check completed", extra={
            "correlation_id": correlation_id,
            "status": health_status,
            "issues_count": len(issues)
        })
        
        return health_check
        
    except Exception as e:
        logger.error("Webhook health check failed", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        
        return WebhookHealthCheck(
            status="unhealthy",
            database="unknown",
            signature_verification="unknown",
            event_processing="unknown",
            stats=WebhookStats(
                total_events=0,
                successful_deliveries=0,
                failed_deliveries=0,
                pending_deliveries=0,
                events_last_24h=0,
                success_rate_24h=0.0
            ),
            issues=[f"Health check failed: {str(e)}"]
        )


@router.get("/stats", response_model=WebhookStats)
async def get_webhook_stats(
    correlation_id: CorrelationID,
    webhook_service: WebhookServiceDep
) -> WebhookStats:
    """
    Get webhook delivery statistics.
    
    This endpoint:
    - Returns webhook delivery statistics
    - Includes success rates and error breakdowns
    - Useful for monitoring and analytics
    """
    try:
        logger.info("Webhook stats requested", extra={
            "correlation_id": correlation_id
        })
        
        stats = await webhook_service.get_webhook_stats()
        
        logger.info("Webhook stats retrieved", extra={
            "correlation_id": correlation_id,
            "total_events": stats.total_events,
            "success_rate_24h": stats.success_rate_24h
        })
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get webhook stats", extra={
            "correlation_id": correlation_id,
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhook statistics"
        )


@router.post("/retry/{event_id}")
async def retry_webhook_event(
    event_id: str,
    correlation_id: CorrelationID,
    webhook_service: WebhookServiceDep
) -> WebhookResponse:
    """
    Retry a failed webhook event.
    
    This endpoint:
    - Retries a specific webhook event
    - Useful for manual intervention
    - Respects retry limits and backoff
    """
    try:
        logger.info("Webhook retry requested", extra={
            "correlation_id": correlation_id,
            "event_id": event_id
        })
        
        result = await webhook_service.retry_webhook_event(
            event_id=event_id,
            correlation_id=correlation_id
        )
        
        if result.get("success", False):
            logger.info("Webhook retry successful", extra={
                "correlation_id": correlation_id,
                "event_id": event_id
            })
            
            return WebhookResponse(
                success=True,
                message="Webhook event retried successfully",
                correlation_id=correlation_id
            )
        else:
            logger.warning("Webhook retry failed", extra={
                "correlation_id": correlation_id,
                "event_id": event_id,
                "error": result.get("error")
            })
            
            return WebhookResponse(
                success=False,
                message=f"Webhook retry failed: {result.get('error', 'Unknown error')}",
                correlation_id=correlation_id
            )
        
    except Exception as e:
        logger.error("Webhook retry error", extra={
            "correlation_id": correlation_id,
            "event_id": event_id,
            "error": str(e)
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook retry failed"
        )
