"""orders foundation

Creates orders, order_items, order_status_events, and order_outbox_events — the
Launch Sprint checkout/order-creation schema. No Odoo or payment columns here (those
land in their own migrations, 0005+) — this migration only covers "what the customer
ordered, what it costs, and its status history," per data-ownership separation.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
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

_ORDER_STATUSES = "('pending_payment', 'paid', 'processing', 'delivered', 'cancelled')"
_OUTBOX_EVENT_TYPES = "('order.created', 'order.paid')"
_OUTBOX_STATUSES = "('pending', 'processing', 'completed', 'failed')"


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending_payment"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="SAR"),
        sa.Column("subtotal_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("promo_code", sa.String(length=32), nullable=True),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("delivery_fee_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("is_gift", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("identity_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("recipient_phone", sa.String(length=32), nullable=False),
        sa.Column("delivery_area", sa.String(length=255), nullable=True),
        sa.Column("delivery_address", sa.String(length=500), nullable=True),
        sa.Column("delivery_address_extra", sa.String(length=255), nullable=True),
        sa.Column("delivery_date", sa.String(length=64), nullable=True),
        sa.Column("delivery_time", sa.String(length=64), nullable=True),
        sa.Column("tracking_token", sa.String(length=64), nullable=False),
        sa.Column("recipient_confirmation_token", sa.String(length=64), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.CheckConstraint(f"status IN {_ORDER_STATUSES}", name="ck_orders_status"),
        sa.CheckConstraint("subtotal_amount >= 0", name="ck_orders_subtotal_nonneg"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonneg"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_orders_tax_nonneg"),
        sa.CheckConstraint("delivery_fee_amount >= 0", name="ck_orders_delivery_fee_nonneg"),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonneg"),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_tracking_token", "orders", ["tracking_token"], unique=True)
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("size_label", sa.String(length=64), nullable=True),
        sa.Column("flavor", sa.String(length=64), nullable=True),
        sa.Column("inscription", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["product_variant_id"], ["catalogue_product_variants.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_nonneg"),
        sa.CheckConstraint("line_total >= 0", name="ck_order_items_line_total_nonneg"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "order_status_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint(f"status IN {_ORDER_STATUSES}", name="ck_order_status_events_status"),
    )
    op.create_index("ix_order_status_events_order_id", "order_status_events", ["order_id"])

    op.create_table(
        "order_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            f"event_type IN {_OUTBOX_EVENT_TYPES}", name="ck_order_outbox_event_type"
        ),
        sa.CheckConstraint(f"status IN {_OUTBOX_STATUSES}", name="ck_order_outbox_status"),
    )
    op.create_index("ix_order_outbox_events_order_id", "order_outbox_events", ["order_id"])
    op.create_index(
        "ix_order_outbox_events_pending",
        "order_outbox_events",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_order_outbox_events_pending", table_name="order_outbox_events")
    op.drop_index("ix_order_outbox_events_order_id", table_name="order_outbox_events")
    op.drop_table("order_outbox_events")

    op.drop_index("ix_order_status_events_order_id", table_name="order_status_events")
    op.drop_table("order_status_events")

    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders_order_number", table_name="orders")
    op.drop_index("ix_orders_tracking_token", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_table("orders")
