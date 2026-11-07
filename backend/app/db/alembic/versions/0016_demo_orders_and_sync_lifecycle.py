"""Demo orders, the simulated sync status, and the order.created lifecycle.

- orders.is_demo: set once at creation, keeps a demo order out of Odoo permanently.
- odoo_sync_status gains "simulated". Rows the stub marked "synced" (the tell: no Odoo sale
  order id) become "simulated", because they were never delivered to Odoo.
- Pending order.created events are completed: they are audit records with no consumer.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.drop_constraint("ck_orders_odoo_sync_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_odoo_sync_status",
        "orders",
        "odoo_sync_status IN ('not_synced', 'synced', 'simulated', 'failed')",
    )
    op.execute(
        "UPDATE orders SET odoo_sync_status = 'simulated', odoo_last_synced_at = NULL "
        "WHERE odoo_sync_status = 'synced' AND odoo_sale_order_id IS NULL"
    )
    op.execute(
        "UPDATE order_outbox_events SET status = 'completed', processed_at = now() "
        "WHERE event_type = 'order.created' AND status = 'pending'"
    )


def downgrade() -> None:
    # The order.created completions are left in place: pending was never a meaningful state
    # for an event nothing consumes, and restoring it would bring back a false backlog.
    op.execute("UPDATE orders SET odoo_sync_status = 'synced' WHERE odoo_sync_status = 'simulated'")
    op.drop_constraint("ck_orders_odoo_sync_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_odoo_sync_status",
        "orders",
        "odoo_sync_status IN ('not_synced', 'synced', 'failed')",
    )
    op.drop_column("orders", "is_demo")
