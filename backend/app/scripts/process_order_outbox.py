"""Manually drive the paid-order -> Odoo outbox consumer (normally run by Celery Beat
every 60s, see app/workers/celery_app.py). Useful for local verification without a
Redis broker running, or as an ops fallback if Beat/the worker is down.

Usage (from the backend/ virtualenv, migrations already applied):
    python -m app.scripts.process_order_outbox
"""

from __future__ import annotations

import sys

from app.core.database import session_scope
from app.services.checkout.odoo_sync_service import OdooOrderSyncService


def main(argv: list[str] | None = None) -> int:
    with session_scope() as session:
        summary = OdooOrderSyncService(session).sync_paid_orders()

    print(f"Odoo order sync: processed={summary.processed}")
    print(f"  succeeded={summary.succeeded} failed={summary.failed}")
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
