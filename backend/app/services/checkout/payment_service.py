"""Payment confirmation: charges a pending_payment order via the configured
PaymentProvider, records the attempt, and — on success — transitions the order to
paid, appends a status event, and enqueues both the `order.paid` (Odoo sync) and
`order.notify` (customer email/SMS) outbox events, all in the caller's transaction
(same rule-8 guarantee as OrderService.create_order). Two event rows, not one shared
one: OdooOrderSyncService and NotificationService are independent consumers, and each
outbox row has a single status column — sharing one would let whichever consumer runs
first mark it completed and hide it from the other.

Never charges an order that isn't pending_payment (ConflictError) — this is what makes
double-submitting the payment button, or retrying after a network blip, safe.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, PaymentDeclinedError
from app.integrations.payments import get_payment_provider
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_payment import OrderPayment
from app.models.orders.order_status_event import OrderStatusEvent
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_payment_repository import OrderPaymentRepository
from app.repositories.orders.order_repository import OrderRepository


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.payments = OrderPaymentRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.settings = get_settings()

    def pay_order(self, order_id: uuid.UUID, method_label: str) -> Order:
        order = self.orders.get_by_id_with_items(order_id)
        if order is None:
            raise NotFoundError(f"No order found with id {order_id}.")
        if order.status != "pending_payment":
            raise ConflictError(
                f"Order {order.order_number} is {order.status!r}, not awaiting payment."
            )

        provider = get_payment_provider(self.settings)
        result = provider.charge(
            amount=float(order.total_amount),
            currency=order.currency,
            method_label=method_label,
            order_number=order.order_number,
        )

        self.payments.create(
            OrderPayment(
                order_id=order.id,
                provider=provider.name,
                method_label=method_label,
                amount=order.total_amount,
                currency=order.currency,
                status=result.status,
                provider_reference=result.provider_reference,
                raw_response=result.raw,
            )
        )

        if not result.success:
            raise PaymentDeclinedError(f"Payment for order {order.order_number} was declined.")

        order.status = "paid"
        self.session.flush()
        self.orders.add_status_event(OrderStatusEvent(order_id=order.id, status="paid"))
        self.outbox.create(
            OrderOutboxEvent(
                order_id=order.id,
                event_type="order.paid",
                payload={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "provider_reference": result.provider_reference,
                },
            )
        )
        self.outbox.create(
            OrderOutboxEvent(
                order_id=order.id,
                event_type="order.notify",
                payload={"order_id": str(order.id), "order_number": order.order_number},
            )
        )

        return order
