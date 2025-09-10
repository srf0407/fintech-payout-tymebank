from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from ..models.payout import PayoutStatus


class PayoutCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    amount: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(..., min_length=3, max_length=3)
    metadata_json: Optional[dict[str, Any]] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3:
            raise ValueError("currency must be 3 characters (ISO 4217)")
        return v.upper()


class PayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    user_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: PayoutStatus
    provider_reference: Optional[str] = None
    provider_status: Optional[str] = None
    idempotency_key: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    retry_count: int
    last_attempt_at: Optional[datetime] = None
    webhook_received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    correlation_id: Optional[str] = None


class PayoutList(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[PayoutRead]
    page: int
    page_size: int
    total: int


