"""Order creation and lookup.

POST /orders prices the submitted cart against PostgreSQL (never trusts a
client-submitted price) and persists the order, its items, its first status event, and
its `order.created` outbox event in one transaction — this handler commits exactly once,
after OrderService returns, so a partially-created order can never be visible to another
request (CLAUDE.md rule 8). No Odoo call happens here; that's the outbox consumer's job.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.schemas.checkout import (
    CheckoutRequest,
    OrderItemAttributeOut,
    OrderItemOut,
    OrderOut,
    OrderStatusEventOut,
    PayOrderRequest,
)
from app.core.exceptions import NotFoundError
from app.dependencies import get_db
from app.models.orders.order import Order
from app.models.orders.order_item import OrderItem
from app.repositories.orders.order_repository import OrderRepository
from app.services.checkout.order_service import OrderService
from app.services.checkout.payment_service import PaymentService
from app.workers.tasks.order_notifications import send_order_confirmations
from app.workers.tasks.order_sync import push_paid_orders_to_odoo

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger("app.api.v1.endpoints.orders")


def _money(amount: Any) -> str:
    return f"{float(amount):.2f}"


def _item_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        id=str(item.id),
        sku=item.sku,
        name_en=item.name_en,
        attributes=[OrderItemAttributeOut(**a) for a in (item.attributes_json or [])],
        inscription=item.inscription,
        quantity=item.quantity,
        unit_price=_money(item.unit_price),
        line_total=_money(item.line_total),
    )


def _latest_payment_method(order: Order) -> str | None:
    """The label of the most recent successful payment — orders can only ever have
    zero or one succeeded payment (pay_order refuses a non-pending_payment order), so
    "most recent" only matters in the retry-after-declined case."""
    succeeded = [p for p in order.payments if p.status == "succeeded"]
    if not succeeded:
        return None
    return max(succeeded, key=lambda p: p.created_at).method_label


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        order_number=order.order_number,
        status=order.status,
        currency=order.currency,
        subtotal_amount=_money(order.subtotal_amount),
        discount_amount=_money(order.discount_amount),
        promo_code=order.promo_code,
        tax_amount=_money(order.tax_amount),
        delivery_fee_amount=_money(order.delivery_fee_amount),
        total_amount=_money(order.total_amount),
        is_gift=order.is_gift,
        recipient_name=order.recipient_name,
        recipient_phone=order.recipient_phone,
        delivery_area=order.delivery_area,
        delivery_address=order.delivery_address,
        delivery_address_extra=order.delivery_address_extra,
        delivery_date=order.delivery_date,
        delivery_time=order.delivery_time,
        tracking_token=order.tracking_token,
        payment_method=_latest_payment_method(order),
        items=[_item_out(item) for item in order.items],
        status_history=[
            OrderStatusEventOut(status=e.status, occurred_at=e.occurred_at)
            for e in sorted(order.status_events, key=lambda e: e.occurred_at)
        ],
        created_at=order.created_at,
    )


@router.post("", summary="Price a cart and create an order (status: pending_payment)")
def create_order(request: CheckoutRequest, session: Session = Depends(get_db)) -> OrderOut:
    order = OrderService(session).create_order(request)
    session.commit()
    session.refresh(order)
    return _order_out(order)


@router.post("/{order_id}/pay", summary="Charge a pending_payment order (stub provider)")
def pay_order(
    order_id: uuid.UUID, request: PayOrderRequest, session: Session = Depends(get_db)
) -> OrderOut:
    order = PaymentService(session).pay_order(order_id, request.method_label)
    session.commit()
    session.refresh(order)

    # Best-effort nudges: Celery Beat's periodic polls (60s Odoo, 30s notifications)
    # are what actually guarantee these run, so a broker hiccup here must never fail
    # an already-confirmed payment response back to the customer.
    try:
        push_paid_orders_to_odoo.delay()
    except Exception:
        logger.warning("odoo_sync_dispatch_failed", extra={"order_id": str(order.id)})
    try:
        send_order_confirmations.delay()
    except Exception:
        logger.warning("order_notification_dispatch_failed", extra={"order_id": str(order.id)})

    return _order_out(order)


@router.get("/{order_id}", summary="Fetch an order by id")
def get_order(order_id: uuid.UUID, session: Session = Depends(get_db)) -> OrderOut:
    order = OrderRepository(session).get_by_id_with_items(order_id)
    if order is None:
        raise NotFoundError(f"No order found with id {order_id}.")
    return _order_out(order)


@router.get("/by-tracking-token/{tracking_token}", summary="Fetch an order by its tracking token")
def get_order_by_tracking_token(
    tracking_token: str, session: Session = Depends(get_db)
) -> OrderOut:
    order = OrderRepository(session).get_by_tracking_token(tracking_token)
    if order is None:
        raise NotFoundError(f"No order found with tracking token {tracking_token!r}.")
    return _order_out(order)
