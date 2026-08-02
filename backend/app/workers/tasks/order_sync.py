"""Celery task wrapping OdooOrderSyncService — the only place a request/response cycle
touches this indirectly (the /orders/{id}/pay endpoint enqueues it after commit; it
never calls the service itself, per CLAUDE.md rule 5).
"""

from __future__ import annotations

import logging

from app.core.database import session_scope
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.tasks.order_sync")


@celery_app.task(
    name="app.workers.tasks.order_sync.push_paid_orders_to_odoo",
    # Fire-and-forget: nothing ever calls .get() on this (not the endpoint's .delay()
    # nudge, not Beat's periodic dispatch), so skip writing a result at all — that's
    # what was making the caller wait through the Redis result-backend's own retry
    # policy (up to 20 attempts) whenever the broker/backend was unreachable.
    ignore_result=True,
)
def push_paid_orders_to_odoo() -> dict[str, int]:
    with session_scope() as session:
        summary = OdooOrderSyncService(session).sync_paid_orders()

    logger.info(
        "odoo_order_sync_completed",
        extra={
            "processed": summary.processed,
            "succeeded": summary.succeeded,
            "failed": summary.failed,
        },
    )
    return {
        "processed": summary.processed,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
    }
