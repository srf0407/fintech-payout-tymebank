"""create payouts table

Revision ID: 20250910_000001
Revises: 
Create Date: 2025-09-10 00:00:01

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250910_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    payout_status = postgresql.ENUM(
        "pending", "processing", "succeeded", "failed", "cancelled",
        name="payout_status",
    )
    payout_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum(name="payout_status", native_enum=False), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("provider_status", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retry_count", sa.Numeric(10, 0), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint("reference", name="uq_payouts_reference"),
        sa.UniqueConstraint("idempotency_key", name="uq_payouts_idempotency_key"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_payouts_currency_len_3"),
        sa.CheckConstraint("currency = upper(currency)", name="ck_payouts_currency_upper"),
    )

    op.create_index("ix_payouts_reference", "payouts", ["reference"], unique=False)
    op.create_index("ix_payouts_currency", "payouts", ["currency"], unique=False)
    op.create_index("ix_payouts_status", "payouts", ["status"], unique=False)
    op.create_index("ix_payouts_status_created_at", "payouts", ["status", "created_at"], unique=False)
    op.create_index("ix_payouts_provider_reference", "payouts", ["provider_reference"], unique=False)
    op.create_index("ix_payouts_created_at", "payouts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payouts_created_at", table_name="payouts")
    op.drop_index("ix_payouts_provider_reference", table_name="payouts")
    op.drop_index("ix_payouts_status_created_at", table_name="payouts")
    op.drop_index("ix_payouts_status", table_name="payouts")
    op.drop_index("ix_payouts_currency", table_name="payouts")
    op.drop_index("ix_payouts_reference", table_name="payouts")
    op.drop_table("payouts")

    payout_status = postgresql.ENUM(
        "pending", "processing", "succeeded", "failed", "cancelled",
        name="payout_status",
    )
    payout_status.drop(op.get_bind(), checkfirst=True)


