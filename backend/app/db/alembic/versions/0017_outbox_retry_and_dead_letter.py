"""Automatic retry scheduling and a dead-letter state for outbox events.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "order_outbox_events",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("ck_order_outbox_status", "order_outbox_events", type_="check")
    op.create_check_constraint(
        "ck_order_outbox_status",
        "order_outbox_events",
        "status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter')",
    )


def downgrade() -> None:
    op.execute("UPDATE order_outbox_events SET status = 'failed' WHERE status = 'dead_letter'")
    op.drop_constraint("ck_order_outbox_status", "order_outbox_events", type_="check")
    op.create_check_constraint(
        "ck_order_outbox_status",
        "order_outbox_events",
        "status IN ('pending', 'processing', 'completed', 'failed')",
    )
    op.drop_column("order_outbox_events", "next_attempt_at")
