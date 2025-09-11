"""
Webhook schemas for payment provider notifications.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    
    PAYMENT_CREATED = "payment.created"
    PAYMENT_UPDATED = "payment.updated"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_CANCELLED = "payment.cancelled"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_STATUS_CHANGED = "payment.status_changed"


class WebhookSignatureType(str, Enum):
    """Supported webhook signature types."""
    
    HMAC_SHA256 = "hmac_sha256"
    HMAC_SHA1 = "hmac_sha1"
    JWT = "jwt"


class WebhookSignature(BaseModel):
    """Webhook signature information."""
    
    type: WebhookSignatureType = Field(..., description="Signature type")
    value: str = Field(..., description="Signature value")
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class WebhookRequest(BaseModel):
    """Incoming webhook request."""
    
    event_type: WebhookEventType = Field(..., description="Webhook event type")
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    payment_id: str = Field(..., description="Payment provider ID")
    reference: str = Field(..., description="Payment reference")
    status: str = Field(..., description="Payment status")
    
    amount: Optional[float] = Field(None, description="Payment amount")
    currency: Optional[str] = Field(None, description="Payment currency")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) != 3:
            raise ValueError("Currency must be 3 characters")
        return v.upper() if v else v


class WebhookResponse(BaseModel):
    """Webhook response."""
    
    success: bool = Field(..., description="Whether webhook was processed successfully")
    message: str = Field(..., description="Response message")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class WebhookErrorResponse(BaseModel):
    """Webhook error response."""
    
    error: str = Field(..., description="Error code")
    error_description: str = Field(..., description="Error description")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class WebhookVerificationRequest(BaseModel):
    """Request to verify webhook signature."""
    
    payload: bytes = Field(..., description="Raw webhook payload")
    signature: WebhookSignature = Field(..., description="Signature information")
    timestamp: Optional[str] = Field(None, description="Request timestamp")


class WebhookEvent(BaseModel):
    """Processed webhook event."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Event ID")
    event_type: WebhookEventType = Field(..., description="Event type")
    event_id: str = Field(..., description="External event ID")
    payment_id: str = Field(..., description="Payment provider ID")
    reference: str = Field(..., description="Payment reference")
    
    status: str = Field(..., description="Payment status")
    error_code: Optional[str] = Field(None, description="Error code")
    error_message: Optional[str] = Field(None, description="Error message")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")
    
    # Timestamps
    event_timestamp: datetime = Field(..., description="Event timestamp")
    received_at: datetime = Field(..., description="When webhook was received")
    processed_at: Optional[datetime] = Field(None, description="When event was processed")
    
    # Correlation
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    retry_count: int = Field(default=0, description="Number of retry attempts")


class WebhookDeliveryAttempt(BaseModel):
    """Webhook delivery attempt record."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Attempt ID")
    webhook_event_id: UUID = Field(..., description="Related webhook event ID")
    
    url: str = Field(..., description="Webhook delivery URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    
    status_code: Optional[int] = Field(None, description="HTTP status code")
    response_body: Optional[str] = Field(None, description="Response body")
    response_headers: Optional[Dict[str, str]] = Field(None, description="Response headers")
    
    attempted_at: datetime = Field(..., description="Attempt timestamp")
    duration_ms: Optional[int] = Field(None, description="Request duration in milliseconds")
    
    success: bool = Field(..., description="Whether delivery was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    retry_count: int = Field(default=0, description="Retry attempt number")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")


class WebhookSubscription(BaseModel):
    """Webhook subscription configuration."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Subscription ID")
    name: str = Field(..., description="Subscription name")
    url: str = Field(..., description="Webhook URL")
    
    event_types: List[WebhookEventType] = Field(..., description="Subscribed event types")
    
    secret: str = Field(..., description="Webhook secret for signature verification")
    signature_type: WebhookSignatureType = Field(..., description="Signature type")
    
    active: bool = Field(default=True, description="Whether subscription is active")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=60, description="Delay between retries")
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_delivery_at: Optional[datetime] = Field(None, description="Last successful delivery")


