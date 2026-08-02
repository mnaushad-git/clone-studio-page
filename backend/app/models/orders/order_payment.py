"""Payment attempt record — one row per charge attempt against a payment provider.

`provider` is never hardcoded to a specific gateway in application logic; it's just
whatever app.integrations.payments.factory currently returns (Launch Sprint: "stub",
which never contacts a real gateway). Swapping in a real provider later is a config
change plus a new app.integrations.payments module — this table's shape doesn't change.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.orders.order import Order

PAYMENT_STATUSES = ("succeeded", "failed")


class OrderPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_payments"
    __table_args__ = (
        CheckConstraint(f"status IN {PAYMENT_STATUSES}", name="ck_order_payments_status"),
        CheckConstraint("amount >= 0", name="ck_order_payments_amount_nonneg"),
        Index("ix_order_payments_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    method_label: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128))
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    order: Mapped[Order] = relationship("Order", back_populates="payments")
