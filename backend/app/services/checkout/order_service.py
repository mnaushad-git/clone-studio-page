"""Order creation. Prices the cart (CheckoutPricingService) then persists the order,
its line items, its first status event, and its `order.created` outbox event — all via
repository .add()/.flush() calls in the caller's transaction, never a commit here
(app/repositories/base.py: "session lifecycle is owned by the caller"). The route
handler commits once, after this returns, so an Order and its outbox event can never
exist independently of one another (CLAUDE.md rule 8).
"""

from __future__ import annotations

import secrets
import string

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.schemas.checkout import CheckoutRequest
from app.models.orders.order import Order
from app.models.orders.order_item import OrderItem
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_status_event import OrderStatusEvent
from app.repositories.admin.promo_code_repository import PromoCodeRepository
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository
from app.services.checkout.pricing_service import CheckoutPricingService

_ORDER_NUMBER_ALPHABET = string.ascii_uppercase + string.digits
_MAX_ORDER_NUMBER_ATTEMPTS = 5


def _generate_order_number() -> str:
    suffix = "".join(secrets.choice(_ORDER_NUMBER_ALPHABET) for _ in range(6))
    return f"TB-{suffix}"


def _generate_tracking_token(order_number: str) -> str:
    return "tk-" + order_number.lower().replace("-", "")


class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.pricing = CheckoutPricingService(session)
        self.orders = OrderRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.promo_codes = PromoCodeRepository(session)

    def create_order(self, request: CheckoutRequest) -> Order:
        self.pricing.validate_delivery_slot(request.delivery.delivery_time)
        pricing = self.pricing.price_cart(request.items, request.promo_code)

        for attempt in range(_MAX_ORDER_NUMBER_ATTEMPTS):
            order_number = _generate_order_number()
            savepoint = self.session.begin_nested()
            try:
                order = Order(
                    order_number=order_number,
                    status="pending_payment",
                    currency=pricing.currency,
                    subtotal_amount=pricing.subtotal_amount,
                    discount_amount=pricing.discount_amount,
                    promo_code=pricing.promo_code,
                    promo_code_id=pricing.promo_code_id,
                    discount_type=pricing.discount_type,
                    discount_value=pricing.discount_value,
                    tax_amount=pricing.tax_amount,
                    delivery_fee_amount=pricing.delivery_fee_amount,
                    total_amount=pricing.total_amount,
                    customer_name=request.customer.name,
                    customer_email=request.customer.email,
                    customer_phone=request.customer.phone,
                    is_gift=request.delivery.is_gift,
                    identity_secret=request.delivery.identity_secret,
                    recipient_name=request.delivery.recipient_name,
                    recipient_phone=request.delivery.recipient_phone,
                    delivery_area=request.delivery.area,
                    delivery_address=request.delivery.address,
                    delivery_address_extra=request.delivery.address_extra,
                    delivery_date=request.delivery.delivery_date,
                    delivery_time=request.delivery.delivery_time,
                    tracking_token=_generate_tracking_token(order_number),
                )
                self.orders.create(order)
                savepoint.commit()
                break
            except IntegrityError:
                savepoint.rollback()
                if attempt == _MAX_ORDER_NUMBER_ATTEMPTS - 1:
                    raise
        else:  # pragma: no cover - unreachable, loop always breaks or raises
            raise RuntimeError("Could not allocate a unique order number.")

        for line in pricing.lines:
            self.orders.add_item(
                OrderItem(
                    order_id=order.id,
                    product_id=line.product.id,
                    product_variant_id=line.variant.id,
                    sku=line.variant.sku,
                    name_en=line.product.name_en,
                    attributes_json=[
                        {
                            "code": a.attribute_code,
                            "name_en": a.attribute_name_en,
                            "value_label_en": a.value_label_en,
                        }
                        for a in sorted(line.variant.attribute_values, key=lambda a: a.created_at)
                    ],
                    inscription=line.inscription,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_total=line.line_total,
                )
            )

        self.orders.add_status_event(OrderStatusEvent(order_id=order.id, status="pending_payment"))

        self.outbox.create(
            OrderOutboxEvent(
                order_id=order.id,
                event_type="order.created",
                payload={"order_id": str(order.id), "order_number": order.order_number},
            )
        )

        if pricing.promo_code_id is not None:
            # Same transaction as the order itself — a promo's usage_count must never
            # drift from how many orders actually claimed it (rule 8's atomicity
            # guarantee, applied to promo accounting too).
            promo = self.promo_codes.get_by_id(pricing.promo_code_id)
            if promo is not None:
                self.promo_codes.update(promo, usage_count=promo.usage_count + 1)

        return order
