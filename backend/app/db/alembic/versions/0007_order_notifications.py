"""order notifications

Creates order_notifications (one row per email/SMS send attempt — Launch Sprint
priority 7, stub provider only) and widens order_outbox_events.event_type to accept
'order.notify'. That's a distinct event type from 'order.paid', not a shared one:
OdooOrderSyncService and NotificationService are independent consumers, and the outbox
table has a single status column per row — if both consumers polled the same
'order.paid' rows, whichever ran first would mark a row 'completed' and hide it from
the other. PaymentService now inserts both event types in the same transaction as the
payment itself (see app/services/checkout/payment_service.py).

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_OLD_OUTBOX_EVENT_TYPES = "('order.created', 'order.paid')"
_NEW_OUTBOX_EVENT_TYPES = "('order.created', 'order.paid', 'order.notify')"
_NOTIFICATION_CHANNELS = "('email', 'sms')"
_NOTIFICATION_STATUSES = "('sent', 'failed')"


def upgrade() -> None:
    op.drop_constraint("ck_order_outbox_event_type", "order_outbox_events", type_="check")
    op.create_check_constraint(
        "ck_order_outbox_event_type",
        "order_outbox_events",
        f"event_type IN {_NEW_OUTBOX_EVENT_TYPES}",
    )

    op.create_table(
        "order_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column("template", sa.String(length=64), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint(
            f"channel IN {_NOTIFICATION_CHANNELS}", name="ck_order_notifications_channel"
        ),
        sa.CheckConstraint(
            f"status IN {_NOTIFICATION_STATUSES}", name="ck_order_notifications_status"
        ),
    )
    op.create_index("ix_order_notifications_order_id", "order_notifications", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_notifications_order_id", table_name="order_notifications")
    op.drop_table("order_notifications")

    op.drop_constraint("ck_order_outbox_event_type", "order_outbox_events", type_="check")
    op.create_check_constraint(
        "ck_order_outbox_event_type",
        "order_outbox_events",
        f"event_type IN {_OLD_OUTBOX_EVENT_TYPES}",
    )
