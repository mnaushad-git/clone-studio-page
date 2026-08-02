"""Admin delivery configuration (task brief §12): the single delivery_settings row
plus delivery_slots CRUD. This is also the data CheckoutPricingService now reads at
order-creation time (app/services/checkout/pricing_service.py) and what the public
GET /api/v1/checkout/delivery-options endpoint serves to the Storefront — an admin
edit here takes effect immediately, no redeploy.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.admin.admin_user import AdminUser
from app.models.admin.delivery_settings import DeliverySettings
from app.models.admin.delivery_slot import DeliverySlot
from app.repositories.admin.delivery_repository import (
    DeliverySettingsRepository,
    DeliverySlotRepository,
)
from app.services.admin.audit_service import AuditService

_VALID_WEEKDAYS = frozenset(range(7))


class DeliveryAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings_repo = DeliverySettingsRepository(session)
        self.slots_repo = DeliverySlotRepository(session)
        self.audit = AuditService(session)

    def get_settings(self) -> DeliverySettings:
        return self.settings_repo.get_singleton()

    def update_settings(
        self, data: dict[str, Any], *, admin: AdminUser, request: Request | None = None
    ) -> DeliverySettings:
        available_days = data.get("available_days")
        if available_days is not None and not set(available_days).issubset(_VALID_WEEKDAYS):
            raise ValidationAppError("available_days must contain weekday integers 0-6.")

        settings = self.get_settings()
        before = {field: getattr(settings, field) for field in data}
        for field, value in data.items():
            setattr(settings, field, value)
        settings.updated_by = admin.id
        self.session.flush()

        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.delivery_settings_updated",
            entity_type="delivery_settings",
            entity_id=str(settings.id),
            before=before,
            after=dict(data),
            request=request,
        )
        return settings

    def list_slots(self) -> Sequence[DeliverySlot]:
        return self.slots_repo.list_all()

    def get_slot(self, slot_id: uuid.UUID) -> DeliverySlot:
        slot = self.slots_repo.get_by_id(slot_id)
        if slot is None:
            raise NotFoundError(f"No delivery slot found with id {slot_id}.")
        return slot

    def create_slot(
        self, data: dict[str, Any], *, admin: AdminUser, request: Request | None = None
    ) -> DeliverySlot:
        slot = DeliverySlot(**data)
        self.slots_repo.create(slot)
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.delivery_slot_created",
            entity_type="delivery_slot",
            entity_id=str(slot.id),
            after=dict(data),
            request=request,
        )
        return slot

    def update_slot(
        self,
        slot_id: uuid.UUID,
        data: dict[str, Any],
        *,
        admin: AdminUser,
        request: Request | None = None,
    ) -> DeliverySlot:
        slot = self.get_slot(slot_id)
        before = {field: getattr(slot, field) for field in data}
        for field, value in data.items():
            setattr(slot, field, value)
        self.session.flush()
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.delivery_slot_updated",
            entity_type="delivery_slot",
            entity_id=str(slot.id),
            before=before,
            after=dict(data),
            request=request,
        )
        return slot

    def delete_slot(
        self, slot_id: uuid.UUID, *, admin: AdminUser, request: Request | None = None
    ) -> None:
        slot = self.get_slot(slot_id)
        label = slot.label
        self.slots_repo.delete(slot)
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.delivery_slot_deleted",
            entity_type="delivery_slot",
            entity_id=str(slot_id),
            before={"label": label},
            request=request,
        )
