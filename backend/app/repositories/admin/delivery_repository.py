"""Repositories for delivery_settings (single-row config) and delivery_slots."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.admin.delivery_settings import DeliverySettings
from app.models.admin.delivery_slot import DeliverySlot
from app.repositories.base import BaseRepository


class DeliverySettingsRepository(BaseRepository[DeliverySettings]):
    model = DeliverySettings

    def get_singleton(self) -> DeliverySettings:
        """There is always exactly one row (seeded by migration 0010) — a missing row
        would mean the migration never ran, which is a startup-time bug, not a
        request-time 404."""
        stmt = select(DeliverySettings).limit(1)
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise RuntimeError("delivery_settings has no row — migration 0010 did not seed it.")
        return row


class DeliverySlotRepository(BaseRepository[DeliverySlot]):
    model = DeliverySlot

    def list_all(self) -> Sequence[DeliverySlot]:
        stmt = select(DeliverySlot).order_by(DeliverySlot.display_order, DeliverySlot.start_time)
        return self.session.execute(stmt).scalars().all()

    def list_active(self) -> Sequence[DeliverySlot]:
        stmt = (
            select(DeliverySlot)
            .where(DeliverySlot.active.is_(True))
            .order_by(DeliverySlot.display_order, DeliverySlot.start_time)
        )
        return self.session.execute(stmt).scalars().all()

    def delete(self, slot: DeliverySlot) -> None:
        self.session.delete(slot)
        self.session.flush()
