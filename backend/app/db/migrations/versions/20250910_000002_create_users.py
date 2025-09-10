"""create users table and add user_id to payouts

Revision ID: 20250910_000002
Revises: 20250910_000001
Create Date: 2025-09-10 00:00:02

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20250910_000002"
down_revision = "20250910_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("google_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("picture_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("google_id", name="uq_users_google_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_index("ix_users_google_id", "users", ["google_id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    op.add_column("payouts", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_payouts_user_id", "payouts", ["user_id"], unique=False)
    
    op.create_foreign_key("fk_payouts_user_id", "payouts", "users", ["user_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_payouts_user_id", "payouts", type_="foreignkey")
    op.drop_index("ix_payouts_user_id", table_name="payouts")
    op.drop_column("payouts", "user_id")

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_table("users")
