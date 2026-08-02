"""orders odoo sync

Adds Odoo order-push tracking columns to orders: odoo_sync_status,
odoo_sale_order_id, odoo_last_synced_at. Launch Sprint priority 5 — the pusher itself
is stubbed (app/integrations/odoo/order_push.py), so odoo_sale_order_id stays NULL for
every order today; these columns exist so the outbox consumer has somewhere to record
sync state regardless, and so a real pusher is a config swap, not a schema change.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_ODOO_ORDER_SYNC_STATUSES = "('not_synced', 'synced', 'failed')"


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "odoo_sync_status", sa.String(length=16), nullable=False, server_default="not_synced"
        ),
    )
    op.add_column("orders", sa.Column("odoo_sale_order_id", sa.Integer(), nullable=True))
    op.add_column(
        "orders", sa.Column("odoo_last_synced_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_orders_odoo_sync_status", "orders", f"odoo_sync_status IN {_ODOO_ORDER_SYNC_STATUSES}"
    )


def downgrade() -> None:
    op.drop_constraint("ck_orders_odoo_sync_status", "orders", type_="check")
    op.drop_column("orders", "odoo_last_synced_at")
    op.drop_column("orders", "odoo_sale_order_id")
    op.drop_column("orders", "odoo_sync_status")
