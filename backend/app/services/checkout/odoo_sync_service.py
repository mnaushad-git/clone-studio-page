"""Outbox consumer: pushes paid orders into Odoo. Runs in a Celery worker
(app/workers/tasks/order_sync.py) or the app/scripts/process_order_outbox.py CLI —
never inside a FastAPI request handler (CLAUDE.md rule 5).

Idempotent and retryable (rule 7): an event stays `pending` until this successfully
marks it `completed`, so a crash mid-run just means the next run picks the same event
back up. A push attempt is scoped to one event at a time and commits per-event (not
batched into one giant transaction) — a failure on order 2 of 10 must not roll back
order 1's already-recorded success.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.odoo.order_push import OdooOrderLine, OdooOrderPusher, OdooPushResult
from app.integrations.odoo.order_push_factory import get_odoo_order_pusher
from app.models.orders.order import Order
from app.models.orders.order_item import OrderItem
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.catalogue.product_variant_repository import ProductVariantRepository
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository

logger = logging.getLogger("app.services.checkout.odoo_sync")


def _describe_item(item: OrderItem) -> str:
    """The sale line description: the product, the options chosen and any inscription."""
    parts = [item.name_en]
    parts += [f"{a.get('name_en')}: {a.get('value_label_en')}" for a in item.attributes_json or []]
    if item.inscription:
        parts.append(f"Inscription: {item.inscription}")
    return "\n".join(parts)


def _failure_message(result: OdooPushResult) -> str:
    error = result.raw.get("error") or "Odoo order push returned a non-success result."
    details = result.raw.get("discrepancies")
    return f"{error}: {'; '.join(details)}" if details else str(error)


@dataclass(frozen=True)
class OdooSyncSummary:
    processed: int
    succeeded: int
    failed: int


class OdooOrderSyncService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.variants = ProductVariantRepository(session)
        self.settings = get_settings()

    def sync_paid_orders(self, limit: int = 50) -> OdooSyncSummary:
        pusher = get_odoo_order_pusher(self.settings)

        succeeded = 0
        failed = 0
        for _ in range(limit):
            event = self.outbox.claim_next_due("order.paid", datetime.now(UTC))
            if event is None:
                break
            if self._process_event(event, pusher):
                succeeded += 1
            else:
                failed += 1
            # Commit per event: one order's outcome must never be rolled back by a
            # later order's failure in the same batch.
            self.session.commit()

        return OdooSyncSummary(processed=succeeded + failed, succeeded=succeeded, failed=failed)

    def _retry_delay(self, attempts: int) -> timedelta:
        # A timed-out create may still be committing inside Odoo. The next attempt's
        # duplicate check can only see it once it has finished, so never retry sooner than
        # a request could still be in flight.
        settings = self.settings
        base = max(settings.order_sync_retry_base_seconds, 2 * settings.odoo_timeout_seconds)
        delay = base * 2 ** (attempts - 1)
        return timedelta(seconds=min(settings.order_sync_retry_max_seconds, delay))

    def _record_push_failure(self, event: OrderOutboxEvent, order: Order, error: str) -> None:
        event.attempts += 1
        event.last_error = error
        order.odoo_sync_status = "failed"
        if event.attempts >= self.settings.order_sync_max_attempts:
            event.status = "dead_letter"
            event.next_attempt_at = None
            logger.error(
                "odoo_order_sync_dead_lettered",
                extra={"order_id": str(order.id), "attempts": event.attempts},
            )
            return
        event.status = "failed"
        event.next_attempt_at = datetime.now(UTC) + self._retry_delay(event.attempts)

    def _resolve_odoo_variant_id(self, product_variant_id: uuid.UUID | None) -> int | None:
        if product_variant_id is None:
            return None
        variant = self.variants.get_by_id(product_variant_id)
        return variant.odoo_product_variant_id if variant else None

    def _process_event(self, event: OrderOutboxEvent, pusher: OdooOrderPusher) -> bool:
        order = self.orders.get_by_id_with_items(event.order_id)
        if order is None:
            event.status = "failed"
            event.attempts += 1
            event.last_error = f"Order {event.order_id} no longer exists."
            return False

        if order.is_demo:
            # Checked per order, not per deployment: a demo order must stay out of Odoo
            # even if this database is later run with the live pusher.
            event.status = "completed"
            event.processed_at = datetime.now(UTC)
            order.odoo_sync_status = "simulated"
            return True

        event.status = "processing"
        self.session.flush()

        try:
            result = pusher.push_order(
                order_number=order.order_number,
                total_amount=float(order.total_amount),
                tax_amount=float(order.tax_amount),
                discount_amount=float(order.discount_amount),
                delivery_fee_amount=float(order.delivery_fee_amount),
                promo_code=order.promo_code,
                currency=order.currency,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone,
                lines=[
                    OdooOrderLine(
                        sku=item.sku,
                        name_en=item.name_en,
                        quantity=item.quantity,
                        unit_price=float(item.unit_price),
                        odoo_variant_id=self._resolve_odoo_variant_id(item.product_variant_id),
                        description=_describe_item(item),
                    )
                    for item in order.items
                ],
            )
        except Exception as exc:  # noqa: BLE001 - any pusher failure is recorded, never crashes the batch
            logger.exception("odoo_order_push_raised", extra={"order_id": str(order.id)})
            self._record_push_failure(event, order, str(exc))
            return False

        if not result.success:
            self._record_push_failure(event, order, _failure_message(result))
            return False

        event.status = "completed"
        event.processed_at = datetime.now(UTC)
        event.next_attempt_at = None
        if result.simulated:
            order.odoo_sync_status = "simulated"
            return True

        order.odoo_sync_status = "synced"
        order.odoo_sale_order_id = result.odoo_sale_order_id
        order.odoo_last_synced_at = datetime.now(UTC)
        return True
