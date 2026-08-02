"""Admin-managed delivery time slots (e.g. "8:00am - 10:00am"). Replaces the Admin
Portal's local-only `slots` array (src/lib/admin-store.ts) as the source both the
Storefront's slot picker and CheckoutPricingService's slot validation read from.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliverySlot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_slots"
    __table_args__ = (Index("ix_delivery_slots_active", "active"),)

    label: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    max_orders_per_slot: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"DeliverySlot(id={self.id!s}, label={self.label!r}, active={self.active!r})"
