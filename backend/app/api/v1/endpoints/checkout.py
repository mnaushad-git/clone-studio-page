"""Public checkout-support endpoints — not order creation itself (that's
app/api/v1/endpoints/orders.py), but read-only config the Storefront needs before
submitting an order. GET /delivery-options replaces the Storefront's local
admin-store zones/slots fallback (task brief §12): the server is the only source of
truth for delivery fee/slots, matching CheckoutPricingService's own read path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.schemas.admin_delivery import DeliveryOptionsOut, DeliverySlotOut
from app.dependencies import get_db
from app.repositories.admin.delivery_repository import (
    DeliverySettingsRepository,
    DeliverySlotRepository,
)

router = APIRouter(prefix="/checkout", tags=["checkout"])


def _money(amount: object) -> str:
    return f"{float(amount):.2f}"  # type: ignore[arg-type]


@router.get("/delivery-options", summary="Current delivery pricing and active slots")
def get_delivery_options(session: Session = Depends(get_db)) -> DeliveryOptionsOut:
    settings = DeliverySettingsRepository(session).get_singleton()
    slots = DeliverySlotRepository(session).list_active()

    return DeliveryOptionsOut(
        delivery_enabled=settings.delivery_enabled,
        flat_delivery_fee=_money(settings.flat_delivery_fee),
        free_delivery_threshold=_money(settings.free_delivery_threshold),
        minimum_order_amount=_money(settings.minimum_order_amount),
        same_day_delivery_enabled=settings.same_day_delivery_enabled,
        same_day_cutoff_time=settings.same_day_cutoff_time,
        available_days=list(settings.available_days),
        slots=[
            DeliverySlotOut(
                id=str(s.id),
                label=s.label,
                start_time=s.start_time,
                end_time=s.end_time,
                max_orders_per_slot=s.max_orders_per_slot,
                active=s.active,
                display_order=s.display_order,
            )
            for s in slots
        ],
    )
