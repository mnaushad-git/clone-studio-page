"""Admin delivery-configuration endpoints (task brief §12). OPERATIONS_ADMIN +
SUPER_ADMIN only, per the plan's role matrix."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import require_csrf, require_role
from app.api.v1.schemas.admin_delivery import (
    DeliverySettingsOut,
    DeliverySettingsUpdateRequest,
    DeliverySlotCreateRequest,
    DeliverySlotOut,
    DeliverySlotUpdateRequest,
)
from app.dependencies import get_db
from app.models.admin.admin_user import AdminUser
from app.models.admin.delivery_settings import DeliverySettings
from app.models.admin.delivery_slot import DeliverySlot
from app.services.admin.delivery_admin_service import DeliveryAdminService

router = APIRouter(prefix="/delivery-settings", tags=["admin-delivery"])
slots_router = APIRouter(prefix="/delivery-slots", tags=["admin-delivery"])

_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN")


def _money(amount: object) -> str:
    return f"{float(amount):.2f}"  # type: ignore[arg-type]


def _settings_out(settings: DeliverySettings) -> DeliverySettingsOut:
    return DeliverySettingsOut(
        delivery_enabled=settings.delivery_enabled,
        flat_delivery_fee=_money(settings.flat_delivery_fee),
        free_delivery_threshold=_money(settings.free_delivery_threshold),
        minimum_order_amount=_money(settings.minimum_order_amount),
        same_day_delivery_enabled=settings.same_day_delivery_enabled,
        same_day_cutoff_time=settings.same_day_cutoff_time,
        available_days=list(settings.available_days),
    )


def _slot_out(slot: DeliverySlot) -> DeliverySlotOut:
    return DeliverySlotOut(
        id=str(slot.id),
        label=slot.label,
        start_time=slot.start_time,
        end_time=slot.end_time,
        max_orders_per_slot=slot.max_orders_per_slot,
        active=slot.active,
        display_order=slot.display_order,
    )


@router.get("", dependencies=[Depends(require_role(*_ROLES))])
def get_delivery_settings(session: Session = Depends(get_db)) -> DeliverySettingsOut:
    return _settings_out(DeliveryAdminService(session).get_settings())


@router.patch("", dependencies=[Depends(require_csrf)])
def update_delivery_settings(
    body: DeliverySettingsUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> DeliverySettingsOut:
    updates = body.model_dump(exclude_unset=True)
    settings = DeliveryAdminService(session).update_settings(updates, admin=admin, request=request)
    session.commit()
    return _settings_out(settings)


@slots_router.get("", dependencies=[Depends(require_role(*_ROLES))])
def list_delivery_slots(session: Session = Depends(get_db)) -> list[DeliverySlotOut]:
    return [_slot_out(s) for s in DeliveryAdminService(session).list_slots()]


@slots_router.post("", dependencies=[Depends(require_csrf)])
def create_delivery_slot(
    body: DeliverySlotCreateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> DeliverySlotOut:
    slot = DeliveryAdminService(session).create_slot(
        body.model_dump(), admin=admin, request=request
    )
    session.commit()
    return _slot_out(slot)


@slots_router.patch("/{slot_id}", dependencies=[Depends(require_csrf)])
def update_delivery_slot(
    slot_id: uuid.UUID,
    body: DeliverySlotUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> DeliverySlotOut:
    updates = body.model_dump(exclude_unset=True)
    slot = DeliveryAdminService(session).update_slot(slot_id, updates, admin=admin, request=request)
    session.commit()
    return _slot_out(slot)


@slots_router.delete("/{slot_id}", dependencies=[Depends(require_csrf)], status_code=204)
def delete_delivery_slot(
    slot_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> None:
    DeliveryAdminService(session).delete_slot(slot_id, admin=admin, request=request)
    session.commit()
