from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ENUM as PGEnum, NUMERIC
from sqlalchemy.orm import relationship

from ..db.session import Base


class PayoutStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference = Column(String(64), nullable=False, unique=True, index=True)
    
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    amount = Column(NUMERIC(18, 2), nullable=False)
    currency = Column(String(3), nullable=False, index=True)

    status = Column(
        PGEnum(PayoutStatus, name="payout_status", create_type=False),
        nullable=False,
        index=True,
        default=PayoutStatus.pending,
    )

    provider_reference = Column(String(128), nullable=True, index=True)
    provider_status = Column(String(64), nullable=True)

    idempotency_key = Column(String(128), nullable=False, unique=True)

    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    metadata_json = Column(JSONB, nullable=True)

    retry_count = Column(
        NUMERIC(10, 0), nullable=False, server_default="0"
    )
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    correlation_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    user = relationship("User", back_populates="payouts", lazy="select")

    __table_args__ = (
        CheckConstraint("char_length(currency) = 3", name="ck_payouts_currency_len_3"),
        CheckConstraint("currency = upper(currency)", name="ck_payouts_currency_upper"),
        UniqueConstraint("reference", name="uq_payouts_reference"),
        UniqueConstraint("idempotency_key", name="uq_payouts_idempotency_key"),
        Index("ix_payouts_status_created_at", "status", "created_at"),
    )


