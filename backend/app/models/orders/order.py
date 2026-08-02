"""Customer order — created by the checkout flow, priced authoritatively from
catalogue_product_prices at creation time (never trusts a client-submitted total).

Odoo push (order sync) and payment are tracked in their own tables/columns added by
later migrations, not here — keeps this table's concerns to "what the customer
ordered and what it costs" (data-ownership.md-style separation, applied to orders).
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
    from app.models.admin.promo_code import PromoCode
    from app.models.orders.order_item import OrderItem
    from app.models.orders.order_notification import OrderNotification
    from app.models.orders.order_outbox_event import OrderOutboxEvent
    from app.models.orders.order_payment import OrderPayment
    from app.models.orders.order_status_event import OrderStatusEvent

# pending_payment: created, awaiting the payment step (Feature 3).
# paid: payment confirmed. processing/delivered: fulfilment progress (matches the
# existing Storefront's Processing/Paid/Delivered vocabulary, snake_cased).
# cancelled: never paid or refunded before fulfilment.
ORDER_STATUSES = ("pending_payment", "paid", "processing", "delivered", "cancelled")

# not_synced: never attempted (or not yet paid). synced: an OdooOrderPusher call
# succeeded — odoo_sale_order_id is set for a real (non-stub) pusher. failed: the last
# push attempt raised or returned success=False; the outbox event stays retryable.
ODOO_ORDER_SYNC_STATUSES = ("not_synced", "synced", "failed")

# not_required: order was never paid (cancelled from pending_payment) — nothing to
# refund. pending: order had a successful payment when cancelled — a human must
# process the refund through the payment provider's dashboard/support flow; the Admin
# Portal only ever surfaces this state, it never claims to have executed a refund
# (no real payment gateway integration exists yet).
REFUND_STATUSES = ("not_required", "pending")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"status IN {ORDER_STATUSES}", name="ck_orders_status"),
        CheckConstraint(
            f"odoo_sync_status IN {ODOO_ORDER_SYNC_STATUSES}", name="ck_orders_odoo_sync_status"
        ),
        CheckConstraint(
            f"refund_status IS NULL OR refund_status IN {REFUND_STATUSES}",
            name="ck_orders_refund_status",
        ),
        CheckConstraint("subtotal_amount >= 0", name="ck_orders_subtotal_nonneg"),
        CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonneg"),
        CheckConstraint("tax_amount >= 0", name="ck_orders_tax_nonneg"),
        CheckConstraint("delivery_fee_amount >= 0", name="ck_orders_delivery_fee_nonneg"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonneg"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_tracking_token", "tracking_token", unique=True),
        Index("ix_orders_order_number", "order_number", unique=True),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_delivery_date", "delivery_date"),
    )

    order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_payment")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="SAR")

    subtotal_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    promo_code: Mapped[str | None] = mapped_column(String(32))
    # Snapshot of the promo applied at order time — kept alongside promo_code/
    # discount_amount above so a later edit (or deletion) of the PromoCode row never
    # changes what an already-placed order is shown to have received.
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="SET NULL")
    )
    discount_type: Mapped[str | None] = mapped_column(String(16))
    discount_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    delivery_fee_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)

    is_gift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    identity_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_area: Mapped[str | None] = mapped_column(String(255))
    delivery_address: Mapped[str | None] = mapped_column(String(500))
    delivery_address_extra: Mapped[str | None] = mapped_column(String(255))
    delivery_date: Mapped[str | None] = mapped_column(String(64))
    delivery_time: Mapped[str | None] = mapped_column(String(64))

    tracking_token: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_confirmation_token: Mapped[str | None] = mapped_column(String(64))

    odoo_sync_status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_synced")
    odoo_sale_order_id: Mapped[int | None] = mapped_column(Integer)
    odoo_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    refund_status: Mapped[str | None] = mapped_column(String(16))

    promo_code_ref: Mapped[PromoCode | None] = relationship("PromoCode")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    status_events: Mapped[list[OrderStatusEvent]] = relationship(
        "OrderStatusEvent", back_populates="order", cascade="all, delete-orphan"
    )
    outbox_events: Mapped[list[OrderOutboxEvent]] = relationship(
        "OrderOutboxEvent", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list[OrderPayment]] = relationship(
        "OrderPayment", back_populates="order", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[OrderNotification]] = relationship(
        "OrderNotification", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Order(id={self.id!s}, order_number={self.order_number!r}, status={self.status!r})"
