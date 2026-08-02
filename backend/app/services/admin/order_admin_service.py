"""Admin order operations: filtered/paginated listing, detail, controlled status
transitions, and outbox retries.

The status-transition map deliberately reuses the existing 5-state Order model
(pending_payment/paid/processing/delivered/cancelled) rather than introducing the
finer-grained states some specs suggest — CLAUDE.md: "Do not introduce new statuses
if equivalent statuses already exist." `processing` already covers confirmed/
preparing/ready-for-delivery/out-for-delivery. Payment status is never set here —
only the /orders/{id}/pay endpoint (app/services/checkout/payment_service.py) can
move an order into `paid`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.admin.admin_user import AdminUser
from app.models.orders.order import Order
from app.models.orders.order_status_event import OrderStatusEvent
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository
from app.services.admin.audit_service import AuditService
from app.workers.tasks.order_notifications import send_order_confirmations
from app.workers.tasks.order_sync import push_paid_orders_to_odoo

# Admin-settable transitions only. Getting into `paid` from `pending_payment` is the
# payment endpoint's job exclusively — an admin can never fake a payment.
ORDER_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_payment": frozenset({"cancelled"}),
    "paid": frozenset({"processing", "cancelled"}),
    "processing": frozenset({"delivered", "cancelled"}),
    "delivered": frozenset(),
    "cancelled": frozenset(),
}

_EVER_PAID_STATUSES = frozenset({"paid", "processing", "delivered"})


def payment_status_for(order: Order) -> str:
    """ "paid"/"unpaid" derived from order.status (decision 4 in the Admin Portal MVP
    plan) — there is no separate payment_status column. A cancelled order that had
    already been paid still reports "paid" here (refund_status distinguishes it)."""
    if order.status in _EVER_PAID_STATUSES:
        return "paid"
    if order.status == "cancelled" and order.refund_status == "pending":
        return "paid"
    return "unpaid"


@dataclass(frozen=True)
class RetryResult:
    queued: bool
    worker_dispatched: bool
    message: str


class OrderAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.audit = AuditService(session)

    def list_orders(
        self,
        *,
        order_number: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        customer_email: str | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        odoo_sync_status: str | None = None,
        notification_status: str | None = None,
        delivery_date: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "newest",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        statuses: list[str] | None = None
        if status:
            statuses = [status]
        elif payment_status == "unpaid":
            statuses = ["pending_payment"]
        elif payment_status == "paid":
            statuses = ["paid", "processing", "delivered"]

        return self.orders.search_admin(
            order_number=order_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            statuses=statuses,
            odoo_sync_status=odoo_sync_status,
            notification_status=notification_status,
            delivery_date=delivery_date,
            created_from=created_from,
            created_to=created_to,
            sort=sort,
            limit=limit,
            offset=offset,
        )

    def get_order_detail(self, order_id: uuid.UUID) -> Order:
        order = self.orders.get_by_id_with_detail(order_id)
        if order is None:
            raise NotFoundError(f"No order found with id {order_id}.")
        return order

    def update_status(
        self,
        order_id: uuid.UUID,
        new_status: str,
        *,
        note: str | None,
        admin: AdminUser,
        request: Request | None = None,
    ) -> Order:
        order = self.get_order_detail(order_id)
        allowed = ORDER_STATUS_TRANSITIONS.get(order.status, frozenset())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot move order {order.order_number} from {order.status!r} to {new_status!r}."
            )

        if new_status == "cancelled":
            if not note or not note.strip():
                raise ValidationAppError("A reason is required to cancel an order.")
            order.cancellation_reason = note.strip()
            order.refund_status = (
                "pending" if order.status in _EVER_PAID_STATUSES else "not_required"
            )

        before_status = order.status
        order.status = new_status
        self.session.flush()
        self.orders.add_status_event(
            OrderStatusEvent(order_id=order.id, status=new_status, note=note)
        )
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.order_status_updated",
            entity_type="order",
            entity_id=str(order.id),
            before={"status": before_status},
            after={"status": new_status},
            reason=note,
            request=request,
        )
        return order

    def _retry_outbox_event(
        self,
        order_id: uuid.UUID,
        *,
        event_type: str,
        admin: AdminUser,
        request: Request | None,
        action: str,
        dispatch: Callable[[], Any],
    ) -> RetryResult:
        order = self.get_order_detail(order_id)
        events = self.outbox.list_by_order_and_type(order.id, event_type)
        failed = next((e for e in events if e.status == "failed"), None)
        if failed is None:
            raise ConflictError(
                f"Order {order.order_number} has no failed {event_type!r} event to retry."
            )

        failed.status = "pending"
        self.session.flush()
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action=action,
            entity_type="order",
            entity_id=str(order.id),
            after={"outbox_event_id": str(failed.id), "event_type": event_type},
            request=request,
        )

        # Best-effort nudge only — Celery Beat's periodic poll is what guarantees this
        # runs even if the broker is unreachable right now (task brief §9: never
        # pretend a job was queued when the worker is unavailable).
        try:
            dispatch()
            return RetryResult(
                queued=True, worker_dispatched=True, message="Retry queued and dispatched."
            )
        except Exception:  # noqa: BLE001 - broker/Redis being down must not fail the request
            return RetryResult(
                queued=True,
                worker_dispatched=False,
                message=(
                    "Retry queued, but worker infrastructure is unavailable right now — "
                    "it will run on the next scheduled sync."
                ),
            )

    def retry_odoo_sync(
        self, order_id: uuid.UUID, *, admin: AdminUser, request: Request | None = None
    ) -> RetryResult:
        return self._retry_outbox_event(
            order_id,
            event_type="order.paid",
            admin=admin,
            request=request,
            action="admin.odoo_sync_retry_requested",
            dispatch=push_paid_orders_to_odoo.delay,
        )

    def retry_notification(
        self, order_id: uuid.UUID, *, admin: AdminUser, request: Request | None = None
    ) -> RetryResult:
        return self._retry_outbox_event(
            order_id,
            event_type="order.notify",
            admin=admin,
            request=request,
            action="admin.notification_retry_requested",
            dispatch=send_order_confirmations.delay,
        )
