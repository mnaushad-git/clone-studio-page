"""Admin-managed delivery configuration — single-row table (a real settings object,
not a list). Replaces the env-only CHECKOUT_DEFAULT_DELIVERY_FEE/CHECKOUT_FREE_
DELIVERY_THRESHOLD/CHECKOUT_MIN_ORDER_AMOUNT settings as the runtime source of truth
for CheckoutPricingService — those env vars now only seed the migration's initial row,
so an admin can change delivery pricing without a redeploy (task brief §12).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin_user import AdminUser


class DeliverySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "delivery_settings"

    delivery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    flat_delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    free_delivery_threshold: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    minimum_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    same_day_delivery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "HH:MM", 24h — kept as a simple string (matches delivery_time's free-text
    # convention on Order) rather than a DB Time column, since it's only ever compared
    # to a client-supplied clock time, never used in a SQL time computation.
    same_day_cutoff_time: Mapped[str | None] = mapped_column(String(5))
    # Weekday ints, Python convention (Monday=0 .. Sunday=6).
    available_days: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=lambda: [0, 1, 2, 3, 4, 5, 6]
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    updated_by_admin: Mapped[AdminUser | None] = relationship("AdminUser")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"DeliverySettings(id={self.id!s}, flat_delivery_fee={self.flat_delivery_fee!r})"
