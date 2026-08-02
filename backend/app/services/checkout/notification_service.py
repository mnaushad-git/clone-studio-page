"""Outbox consumer: sends the order-confirmation email/SMS. Runs in a Celery worker
(app/workers/tasks/order_notifications.py) or the
app/scripts/process_order_notifications.py CLI — never inside a FastAPI request
handler (CLAUDE.md rule 5). Same per-event-commit, idempotent/retryable shape as
OdooOrderSyncService (app/services/checkout/odoo_sync_service.py) — see that module's
docstring for the reasoning, which applies identically here.

SMS always fires (customer_phone is a required field on Order); email only fires when
customer_email is set — a guest checkout with no email address is not a failure, it's
simply nothing to send there.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.notifications import (
    NotificationProvider,
    NotificationResult,
    get_notification_provider,
)
from app.models.orders.order import Order
from app.models.orders.order_notification import OrderNotification
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.orders.order_notification_repository import OrderNotificationRepository
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository

logger = logging.getLogger("app.services.checkout.notification_service")

CONFIRMATION_TEMPLATE = "order_confirmation"


@dataclass(frozen=True)
class NotificationSyncSummary:
    processed: int
    succeeded: int
    failed: int


def _confirmation_email_body(order: Order) -> tuple[str, str]:
    subject = f"Terrific Bites — order {order.order_number} confirmed"
    body = (
        f"Hi {order.customer_name},\n\n"
        f"Thanks for your order! {order.order_number} is confirmed and being prepared.\n"
        f"Total: {order.currency} {float(order.total_amount):.2f}\n"
        f"Track it: /track/{order.tracking_token}\n"
    )
    return subject, body


def _confirmation_sms_body(order: Order) -> str:
    return (
        f"Terrific Bites: order {order.order_number} confirmed, "
        f"{order.currency} {float(order.total_amount):.2f}. Track: /track/{order.tracking_token}"
    )


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.notifications = OrderNotificationRepository(session)
        self.settings = get_settings()

    def send_pending_confirmations(self, limit: int = 50) -> NotificationSyncSummary:
        provider = get_notification_provider(self.settings)
        events = self.outbox.list_pending(limit=limit, event_type="order.notify")

        succeeded = 0
        failed = 0
        for event in events:
            if self._process_event(event, provider):
                succeeded += 1
            else:
                failed += 1
            # Commit per event — one order's notification outcome must never be rolled
            # back by a later order's failure in the same batch.
            self.session.commit()

        return NotificationSyncSummary(processed=len(events), succeeded=succeeded, failed=failed)

    def _process_event(self, event: OrderOutboxEvent, provider: NotificationProvider) -> bool:
        order = self.orders.get_by_id_with_items(event.order_id)
        if order is None:
            event.status = "failed"
            event.attempts += 1
            event.last_error = f"Order {event.order_id} no longer exists."
            return False

        event.status = "processing"
        self.session.flush()

        try:
            channel_results = self._send_all_channels(order, provider)
        except Exception as exc:  # noqa: BLE001 - any provider failure is recorded, never crashes the batch
            logger.exception("order_notification_raised", extra={"order_id": str(order.id)})
            event.status = "failed"
            event.attempts += 1
            event.last_error = str(exc)
            return False

        if not all(success for _, success in channel_results):
            event.status = "failed"
            event.attempts += 1
            event.last_error = "One or more notification channels failed — see order_notifications."
            return False

        event.status = "completed"
        event.processed_at = datetime.now(UTC)
        return True

    def _send_all_channels(
        self, order: Order, provider: NotificationProvider
    ) -> list[tuple[str, bool]]:
        results: list[tuple[str, bool]] = []

        sms_body = _confirmation_sms_body(order)
        sms_result = provider.send_sms(to=order.customer_phone, body=sms_body)
        self._record(order, provider, "sms", order.customer_phone, sms_result)
        results.append(("sms", sms_result.success))

        if order.customer_email:
            subject, body = _confirmation_email_body(order)
            email_result = provider.send_email(to=order.customer_email, subject=subject, body=body)
            self._record(order, provider, "email", order.customer_email, email_result)
            results.append(("email", email_result.success))

        return results

    def _record(
        self,
        order: Order,
        provider: NotificationProvider,
        channel: str,
        recipient: str,
        result: NotificationResult,
    ) -> None:
        self.notifications.create(
            OrderNotification(
                order_id=order.id,
                channel=channel,
                template=CONFIRMATION_TEMPLATE,
                recipient=recipient,
                provider=provider.name,
                status=result.status,
                provider_reference=result.provider_reference,
                raw_response=result.raw,
            )
        )
