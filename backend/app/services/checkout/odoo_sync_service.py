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
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.odoo.order_push import OdooOrderLine, OdooOrderPusher
from app.integrations.odoo.order_push_factory import get_odoo_order_pusher
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.catalogue.product_variant_repository import ProductVariantRepository
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository

logger = logging.getLogger("app.services.checkout.odoo_sync")


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
        events = self.outbox.list_pending(limit=limit, event_type="order.paid")

        succeeded = 0
        failed = 0
        for event in events:
            if self._process_event(event, pusher):
                succeeded += 1
            else:
                failed += 1
            # Commit per event: one order's outcome must never be rolled back by a
            # later order's failure in the same batch.
            self.session.commit()

        return OdooSyncSummary(processed=len(events), succeeded=succeeded, failed=failed)

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

        event.status = "processing"
        self.session.flush()

        try:
            result = pusher.push_order(
                order_number=order.order_number,
                total_amount=float(order.total_amount),
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
                    )
                    for item in order.items
                ],
            )
        except Exception as exc:  # noqa: BLE001 - any pusher failure is recorded, never crashes the batch
            logger.exception("odoo_order_push_raised", extra={"order_id": str(order.id)})
            event.status = "failed"
            event.attempts += 1
            event.last_error = str(exc)
            order.odoo_sync_status = "failed"
            return False

        if not result.success:
            event.status = "failed"
            event.attempts += 1
            event.last_error = "Odoo order push returned a non-success result."
            order.odoo_sync_status = "failed"
            return False

        event.status = "completed"
        event.processed_at = datetime.now(UTC)
        order.odoo_sync_status = "synced"
        order.odoo_sale_order_id = result.odoo_sale_order_id
        order.odoo_last_synced_at = datetime.now(UTC)
        return True
