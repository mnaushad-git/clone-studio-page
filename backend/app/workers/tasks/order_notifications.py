"""Celery task wrapping NotificationService — see app/workers/tasks/order_sync.py's
docstring for why this is never called directly from a request handler.
"""

from __future__ import annotations

import logging

from app.core.database import session_scope
from app.services.checkout.notification_service import NotificationService
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.tasks.order_notifications")


@celery_app.task(
    name="app.workers.tasks.order_notifications.send_order_confirmations",
    ignore_result=True,
)
def send_order_confirmations() -> dict[str, int]:
    with session_scope() as session:
        summary = NotificationService(session).send_pending_confirmations()

    logger.info(
        "order_notifications_completed",
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
