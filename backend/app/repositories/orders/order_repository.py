from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import selectinload

from app.models.orders.order import Order
from app.models.orders.order_item import OrderItem
from app.models.orders.order_notification import OrderNotification
from app.models.orders.order_status_event import OrderStatusEvent
from app.repositories.base import BaseRepository

_ORDER_LOAD_OPTIONS = (
    selectinload(Order.items),
    selectinload(Order.status_events),
    selectinload(Order.payments),
    # The admin orders list shows a derived "notification status" badge per row
    # (task brief §5) — eager-loading here avoids an N+1 across a page of orders.
    selectinload(Order.notifications),
)

# Full detail view (order-detail admin screen, task brief §6) additionally needs the
# outbox trail and notification history — the list view's _ORDER_LOAD_OPTIONS above
# stays lighter since the admin orders list never renders those.
_ORDER_DETAIL_LOAD_OPTIONS = (
    *_ORDER_LOAD_OPTIONS,
    selectinload(Order.outbox_events),
    selectinload(Order.notifications),
)

_SORT_COLUMNS: dict[str, ColumnElement[Any]] = {
    "newest": Order.created_at.desc(),
    "oldest": Order.created_at.asc(),
    "total_desc": Order.total_amount.desc(),
    "total_asc": Order.total_amount.asc(),
    "delivery_date": Order.delivery_date.asc(),
}


class OrderRepository(BaseRepository[Order]):
    model = Order

    def get_by_id_with_items(self, order_id: object) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).options(*_ORDER_LOAD_OPTIONS)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_tracking_token(self, tracking_token: str) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.tracking_token == tracking_token)
            .options(*_ORDER_LOAD_OPTIONS)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_id_with_detail(self, order_id: object) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).options(*_ORDER_DETAIL_LOAD_OPTIONS)
        return self.session.execute(stmt).scalar_one_or_none()

    def add_item(self, item: OrderItem) -> OrderItem:
        self.session.add(item)
        self.session.flush()
        return item

    def add_status_event(self, event: OrderStatusEvent) -> OrderStatusEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def _admin_filtered_query(
        self,
        *,
        order_number: str | None,
        customer_name: str | None,
        customer_phone: str | None,
        customer_email: str | None,
        statuses: Sequence[str] | None,
        odoo_sync_status: str | None,
        notification_status: str | None,
        delivery_date: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> Select[tuple[Order]]:
        stmt = select(Order)

        if order_number:
            stmt = stmt.where(Order.order_number.ilike(f"%{order_number.strip()}%"))
        if customer_name:
            stmt = stmt.where(Order.customer_name.ilike(f"%{customer_name.strip()}%"))
        if customer_phone:
            stmt = stmt.where(Order.customer_phone.ilike(f"%{customer_phone.strip()}%"))
        if customer_email:
            stmt = stmt.where(Order.customer_email.ilike(f"%{customer_email.strip()}%"))
        if statuses:
            stmt = stmt.where(Order.status.in_(statuses))
        if odoo_sync_status:
            stmt = stmt.where(Order.odoo_sync_status == odoo_sync_status)
        if delivery_date:
            stmt = stmt.where(Order.delivery_date == delivery_date)
        if created_from:
            stmt = stmt.where(Order.created_at >= created_from)
        if created_to:
            stmt = stmt.where(Order.created_at <= created_to)

        if notification_status == "none":
            stmt = stmt.where(
                ~select(OrderNotification.id).where(OrderNotification.order_id == Order.id).exists()
            )
        elif notification_status in ("sent", "failed"):
            stmt = stmt.where(
                select(OrderNotification.id)
                .where(
                    OrderNotification.order_id == Order.id,
                    OrderNotification.status == notification_status,
                )
                .exists()
            )

        return stmt

    def search_admin(
        self,
        *,
        order_number: str | None = None,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        customer_email: str | None = None,
        statuses: Sequence[str] | None = None,
        odoo_sync_status: str | None = None,
        notification_status: str | None = None,
        delivery_date: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "newest",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        """Server-side filtered, sorted, paginated order search for the Admin Portal
        orders list (task brief §5). Returns (page, total_count)."""
        base = self._admin_filtered_query(
            order_number=order_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            statuses=statuses,
            odoo_sync_status=odoo_sync_status,
            notification_status=notification_status,
            delivery_date=delivery_date,
            created_from=created_from,
            created_to=created_to,
        )

        total = self.session.execute(
            select(func.count()).select_from(base.with_only_columns(Order.id).subquery())
        ).scalar_one()

        order_clause = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["newest"])
        page_stmt = (
            base.options(*_ORDER_LOAD_OPTIONS)
            .order_by(order_clause, Order.id)
            .limit(limit)
            .offset(offset)
        )
        items = self.session.execute(page_stmt).scalars().all()
        return items, total

    def list_recent(self, limit: int = 10) -> Sequence[Order]:
        stmt = (
            select(Order)
            .options(*_ORDER_LOAD_OPTIONS)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()

    def count_by_status(self, status: str) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.status == status)
        return self.session.execute(stmt).scalar_one()

    def count_created_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(Order).where(Order.created_at >= since)
        return self.session.execute(stmt).scalar_one()

    def count_created_since_with_status(self, since: datetime, status: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.created_at >= since, Order.status == status)
        )
        return self.session.execute(stmt).scalar_one()

    def sum_total_since(self, since: datetime) -> float:
        stmt = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.created_at >= since, Order.status != "cancelled"
        )
        return float(self.session.execute(stmt).scalar_one())

    def count_stuck(self, threshold: datetime) -> int:
        """Orders sitting in paid/processing with no forward progress since
        `threshold` — the dashboard's "stuck order" alert (task brief §4)."""
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.status.in_(("paid", "processing")), Order.updated_at < threshold)
        )
        return self.session.execute(stmt).scalar_one()

    def count_paid_not_synced(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(
                Order.status.in_(("paid", "processing", "delivered")),
                Order.odoo_sync_status != "synced",
            )
        )
        return self.session.execute(stmt).scalar_one()

    def count_payment_incomplete(self, older_than: datetime) -> int:
        """Orders created but never paid, older than the given cutoff — a likely
        abandoned checkout, not just "still on the payment page"."""
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.status == "pending_payment", Order.created_at < older_than)
        )
        return self.session.execute(stmt).scalar_one()
