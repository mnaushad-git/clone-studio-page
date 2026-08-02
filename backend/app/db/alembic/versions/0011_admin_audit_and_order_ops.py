"""admin audit and order ops

Creates admin_audit_events (append-only administrative audit trail, task brief §13)
and adds orders.cancellation_reason / orders.refund_status so an admin cancellation
always records why and whether a refund is still owed — never fakes a refund, since
no real payment-gateway refund integration exists yet.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_REFUND_STATUSES = "('not_required', 'pending')"


def upgrade() -> None:
    op.create_table(
        "admin_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_admin_audit_events_created_at", "admin_audit_events", ["created_at"])
    op.create_index("ix_admin_audit_events_admin_user_id", "admin_audit_events", ["admin_user_id"])
    op.create_index(
        "ix_admin_audit_events_entity", "admin_audit_events", ["entity_type", "entity_id"]
    )

    op.add_column("orders", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("refund_status", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "ck_orders_refund_status",
        "orders",
        f"refund_status IS NULL OR refund_status IN {_REFUND_STATUSES}",
    )

    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_delivery_date", "orders", ["delivery_date"])


def downgrade() -> None:
    op.drop_index("ix_orders_delivery_date", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")

    op.drop_constraint("ck_orders_refund_status", "orders", type_="check")
    op.drop_column("orders", "refund_status")
    op.drop_column("orders", "cancellation_reason")

    op.drop_index("ix_admin_audit_events_entity", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_admin_user_id", table_name="admin_audit_events")
    op.drop_index("ix_admin_audit_events_created_at", table_name="admin_audit_events")
    op.drop_table("admin_audit_events")
