"""delivery settings

Creates delivery_settings (single-row config) and delivery_slots — the Admin-Portal-
managed replacement for the env-only CHECKOUT_DEFAULT_DELIVERY_FEE/CHECKOUT_FREE_
DELIVERY_THRESHOLD/CHECKOUT_MIN_ORDER_AMOUNT settings and the Storefront's local
DAY_SLOTS fallback (src/routes/delivery.tsx). Seeds one delivery_settings row from
today's env defaults and six two-hour slots matching the existing DAY_SLOTS constant,
so behaviour is unchanged the moment this migration lands — an admin can then edit
either without a redeploy.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-30

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TIMESTAMP_COLUMNS = (
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
)


def upgrade() -> None:
    op.create_table(
        "delivery_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("flat_delivery_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("free_delivery_threshold", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("minimum_order_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "same_day_delivery_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("same_day_cutoff_time", sa.String(length=5), nullable=True),
        sa.Column("available_days", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "delivery_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("max_orders_per_slot", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        *_TIMESTAMP_COLUMNS,
    )
    op.create_index("ix_delivery_slots_active", "delivery_slots", ["active"])

    delivery_settings_table = sa.table(
        "delivery_settings",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("delivery_enabled", sa.Boolean),
        sa.column("flat_delivery_fee", sa.Numeric),
        sa.column("free_delivery_threshold", sa.Numeric),
        sa.column("minimum_order_amount", sa.Numeric),
        sa.column("same_day_delivery_enabled", sa.Boolean),
        sa.column("available_days", postgresql.JSONB),
    )
    op.bulk_insert(
        delivery_settings_table,
        [
            {
                "id": uuid.uuid4(),
                "delivery_enabled": True,
                "flat_delivery_fee": 15.0,
                "free_delivery_threshold": 0.0,
                "minimum_order_amount": 30.0,
                "same_day_delivery_enabled": False,
                "available_days": [0, 1, 2, 3, 4, 5, 6],
            }
        ],
    )

    delivery_slots_table = sa.table(
        "delivery_slots",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("label", sa.String),
        sa.column("start_time", sa.String),
        sa.column("end_time", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        delivery_slots_table,
        [
            {
                "id": uuid.uuid4(),
                "label": label,
                "start_time": start,
                "end_time": end,
                "active": True,
                "display_order": order,
            }
            for order, (label, start, end) in enumerate(
                [
                    ("8:00am - 10:00am", "08:00", "10:00"),
                    ("10:00am - 12:00pm", "10:00", "12:00"),
                    ("12:00pm - 2:00pm", "12:00", "14:00"),
                    ("2:00pm - 4:00pm", "14:00", "16:00"),
                    ("4:00pm - 6:00pm", "16:00", "18:00"),
                    ("6:00pm - 8:00pm", "18:00", "20:00"),
                ]
            )
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_slots_active", table_name="delivery_slots")
    op.drop_table("delivery_slots")
    op.drop_table("delivery_settings")
