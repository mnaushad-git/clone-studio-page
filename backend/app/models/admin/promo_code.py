"""Admin-managed promo codes — replaces the hardcoded WELCOME10/SWEET15/TB20 dict in
app/services/checkout/pricing_service.py and the Storefront's legacy PROMOS mirror
(src/lib/store.ts). `code` is always stored normalized (uppercase, trimmed); the
server is the only place a discount is ever computed (checkout never trusts a
client-submitted percentage).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin_user import AdminUser

DISCOUNT_TYPES = ("PERCENTAGE", "FIXED_AMOUNT")


class PromoCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        CheckConstraint(f"discount_type IN {DISCOUNT_TYPES}", name="ck_promo_codes_discount_type"),
        CheckConstraint("discount_value > 0", name="ck_promo_codes_discount_value_positive"),
        CheckConstraint(
            "discount_type != 'PERCENTAGE' OR discount_value <= 100",
            name="ck_promo_codes_percentage_max_100",
        ),
        CheckConstraint("minimum_order_amount >= 0", name="ck_promo_codes_minimum_order_nonneg"),
        CheckConstraint("usage_count >= 0", name="ck_promo_codes_usage_count_nonneg"),
        CheckConstraint(
            "usage_limit IS NULL OR usage_count <= usage_limit",
            name="ck_promo_codes_usage_within_limit",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="ck_promo_codes_valid_until_after_from",
        ),
        Index("ix_promo_codes_code", "code", unique=True),
        Index("ix_promo_codes_is_active", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    maximum_discount_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    per_customer_limit: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    created_by_admin: Mapped[AdminUser | None] = relationship(
        "AdminUser", foreign_keys=[created_by]
    )
    updated_by_admin: Mapped[AdminUser | None] = relationship(
        "AdminUser", foreign_keys=[updated_by]
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"PromoCode(id={self.id!s}, code={self.code!r}, active={self.is_active!r})"
