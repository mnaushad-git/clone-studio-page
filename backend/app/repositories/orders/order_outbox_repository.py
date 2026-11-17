from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, func, or_, select

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

    def claim_next_due(self, event_type: str, now: datetime) -> OrderOutboxEvent | None:
        """Locks the oldest due event until the caller commits or rolls back, skipping any
        another worker holds. If a worker dies, its transaction ends, the lock goes with it
        and the event stays due. One at a time, because each commit releases every lock the
        transaction holds, which would expose the rest of a batch to a second worker."""
        stmt = (
            select(OrderOutboxEvent)
            .where(
                OrderOutboxEvent.event_type == event_type,
                OrderOutboxEvent.status.in_(("pending", "failed")),
                or_(
                    OrderOutboxEvent.next_attempt_at <= now,
                    and_(
                        OrderOutboxEvent.status == "pending",
                        OrderOutboxEvent.next_attempt_at.is_(None),
                    ),
                ),
            )
            .order_by(OrderOutboxEvent.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_order_and_type(
        self, order_id: uuid.UUID, event_type: str
    ) -> Sequence[OrderOutboxEvent]:
        stmt = (
            select(OrderOutboxEvent)
            .where(OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.event_type == event_type)
            .order_by(OrderOutboxEvent.created_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def count_pending_older_than(self, event_types: Sequence[str], older_than: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(OrderOutboxEvent)
            .where(
                OrderOutboxEvent.status == "pending",
                OrderOutboxEvent.event_type.in_(event_types),
                OrderOutboxEvent.created_at < older_than,
            )
        )
        return self.session.execute(stmt).scalar_one()

    def count_by_type_and_status(self, event_type: str, status: str) -> int:
        stmt = (
            select(func.count())
            .select_from(OrderOutboxEvent)
            .where(OrderOutboxEvent.event_type == event_type, OrderOutboxEvent.status == status)
        )
        return self.session.execute(stmt).scalar_one()
