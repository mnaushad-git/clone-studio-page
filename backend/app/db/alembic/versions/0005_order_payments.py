"""order payments

Creates order_payments — one row per charge attempt against a payment provider
(Launch Sprint: the stub provider in app.integrations.payments, never a real gateway).
Kept separate from 0004_orders.py because payment is its own feature/checkpoint
(Launch Sprint priority 3) with its own audit trail, per data-ownership separation.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_PAYMENT_STATUSES = "('succeeded', 'failed')"


def upgrade() -> None:
    op.create_table(
        "order_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("method_label", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint(f"status IN {_PAYMENT_STATUSES}", name="ck_order_payments_status"),
        sa.CheckConstraint("amount >= 0", name="ck_order_payments_amount_nonneg"),
    )
    op.create_index("ix_order_payments_order_id", "order_payments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_payments_order_id", table_name="order_payments")
    op.drop_table("order_payments")
