"""Notification send record — one row per email/SMS attempt for an order.

Same shape/intent as OrderPayment: `provider` is whatever
app.integrations.notifications.factory currently returns (Launch Sprint: "stub", which
never contacts a real email/SMS provider). A real order can have up to two rows per
notification pass (one per channel) — email is skipped (no row) when the order has no
customer_email; SMS always fires since customer_phone is required.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.orders.order import Order

NOTIFICATION_CHANNELS = ("email", "sms")
NOTIFICATION_STATUSES = ("sent", "failed")


class OrderNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_notifications"
    __table_args__ = (
        CheckConstraint(
            f"channel IN {NOTIFICATION_CHANNELS}", name="ck_order_notifications_channel"
        ),
        CheckConstraint(f"status IN {NOTIFICATION_STATUSES}", name="ck_order_notifications_status"),
        Index("ix_order_notifications_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128))
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    order: Mapped[Order] = relationship("Order", back_populates="notifications")
