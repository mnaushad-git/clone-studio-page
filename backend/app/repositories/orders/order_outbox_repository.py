from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.base import BaseRepository


class OrderOutboxRepository(BaseRepository[OrderOutboxEvent]):
    model = OrderOutboxEvent

    def list_pending(
        self, limit: int = 50, event_type: str | None = None
    ) -> Sequence[OrderOutboxEvent]:
        stmt = select(OrderOutboxEvent).where(OrderOutboxEvent.status == "pending")
        if event_type is not None:
            stmt = stmt.where(OrderOutboxEvent.event_type == event_type)
        stmt = stmt.order_by(OrderOutboxEvent.created_at).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def list_by_order_and_type(
        self, order_id: uuid.UUID, event_type: str
    ) -> Sequence[OrderOutboxEvent]:
        stmt = (
            select(OrderOutboxEvent)
            .where(OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.event_type == event_type)
            .order_by(OrderOutboxEvent.created_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def count_by_type_and_status(self, event_type: str, status: str) -> int:
        stmt = (
            select(func.count())
            .select_from(OrderOutboxEvent)
            .where(OrderOutboxEvent.event_type == event_type, OrderOutboxEvent.status == status)
        )
        return self.session.execute(stmt).scalar_one()
