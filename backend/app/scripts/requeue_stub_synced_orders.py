"""One-off repair: find orders the stub pusher marked odoo_sync_status="synced"
without ever contacting Odoo (the tell: odoo_sale_order_id IS NULL — see the
"synced" status comment in app/models/orders/order.py) and requeue them so a real
push happens next time OdooOrderSyncService runs under ODOO_ORDER_PUSH_PROVIDER=live.

Resets the order to odoo_sync_status="not_synced" and its matching completed
"order.paid" outbox event back to "pending" (attempts/last_error cleared). Does not
call Odoo itself — run app/scripts/process_order_outbox.py (or wait for Celery Beat)
afterwards to actually push.

Usage (from the backend/ virtualenv):
    python -m app.scripts.requeue_stub_synced_orders          # requeue
    python -m app.scripts.requeue_stub_synced_orders --dry-run  # list only, no writes
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.database import session_scope
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent


def main(argv: list[str] | None = None) -> int:
    dry_run = "--dry-run" in (argv if argv is not None else sys.argv[1:])

    with session_scope() as session:
        stmt = select(Order).where(
            Order.odoo_sync_status == "synced",
            Order.odoo_sale_order_id.is_(None),
        )
        orders = session.execute(stmt).scalars().all()

        if not orders:
            print("No falsely-synced orders found.")
            return 0

        for order in orders:
            print(f"order_number={order.order_number} order_id={order.id}")
            if dry_run:
                continue

            order.odoo_sync_status = "not_synced"
            order.odoo_last_synced_at = None

            events_stmt = select(OrderOutboxEvent).where(
                OrderOutboxEvent.order_id == order.id,
                OrderOutboxEvent.event_type == "order.paid",
                OrderOutboxEvent.status == "completed",
            )
            for event in session.execute(events_stmt).scalars().all():
                event.status = "pending"
                event.attempts = 0
                event.last_error = None
                event.processed_at = None

        if dry_run:
            print(f"\n{len(orders)} order(s) would be requeued (--dry-run, no writes made).")
        else:
            session.commit()
            print(f"\nRequeued {len(orders)} order(s). Run process_order_outbox.py to push them.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
