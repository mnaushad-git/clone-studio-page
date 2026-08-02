"""Transactional outbox (CLAUDE.md rule 8): an order's creation and its outbox event
commit in the same PostgreSQL transaction, so "order exists" and "an event to sync it
downstream exists" can never diverge. Background workers (Celery) poll this table and
never write to Odoo — or anywhere else downstream — synchronously inside a request.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.orders.order import Order

OUTBOX_EVENT_TYPES = ("order.created", "order.paid", "order.notify")
OUTBOX_STATUSES = ("pending", "processing", "completed", "failed")


class OrderOutboxEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_outbox_events"
    __table_args__ = (
        CheckConstraint(f"event_type IN {OUTBOX_EVENT_TYPES}", name="ck_order_outbox_event_type"),
        CheckConstraint(f"status IN {OUTBOX_STATUSES}", name="ck_order_outbox_status"),
        Index("ix_order_outbox_events_order_id", "order_id"),
        # The worker's poll query is always "give me pending events", so a partial
        # index on just that status keeps the scan cheap as the table grows.
        Index(
            "ix_order_outbox_events_pending", "created_at", postgresql_where="status = 'pending'"
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped[Order] = relationship("Order", back_populates="outbox_events")
