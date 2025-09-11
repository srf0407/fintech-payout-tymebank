"""add last_webhook_event_id to payouts

Revision ID: 20250910_000003
Revises: 20250910_000002
Create Date: 2025-09-10 00:00:03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250910_000003"
down_revision = "20250910_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payouts", sa.Column("last_webhook_event_id", sa.String(length=128), nullable=True))
    op.create_index("ix_payouts_last_webhook_event_id", "payouts", ["last_webhook_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payouts_last_webhook_event_id", table_name="payouts")
    op.drop_column("payouts", "last_webhook_event_id")
