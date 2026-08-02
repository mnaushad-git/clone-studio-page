"""Admin dashboard aggregates (task brief §4). "Today" is a UTC calendar-day
boundary — this codebase has no per-store timezone concept yet (every timestamp is
stored UTC), so this is a known simplification, not a silent Asia/Riyadh assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.orders.order import Order
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.repositories.orders.order_repository import OrderRepository


@dataclass(frozen=True)
class DashboardSummary:
    orders_today: int
    revenue_today: float
    paid_orders_today: int
    pending_payment_orders_today: int
    awaiting_odoo_sync: int
    failed_odoo_sync: int
    failed_notifications: int
    stuck_orders: int
    orders_requiring_attention: int


@dataclass(frozen=True)
class DashboardAlert:
    type: str
    message: str
    count: int


def _today_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class DashboardService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.orders = OrderRepository(session)
        self.outbox = OrderOutboxRepository(session)
        self.settings = settings or get_settings()

    def summary(self, *, now: datetime | None = None) -> DashboardSummary:
        now = now or datetime.now(UTC)
        today_start = _today_start(now)
        stuck_threshold = now - timedelta(minutes=self.settings.ops_stuck_order_minutes)
        payment_incomplete_threshold = now - timedelta(
            minutes=self.settings.ops_stuck_order_minutes
        )

        orders_today = self.orders.count_created_since(today_start)
        revenue_today = self.orders.sum_total_since(today_start)
        paid_orders_today = self.orders.count_created_since_with_status(today_start, "paid")
        pending_payment_orders_today = self.orders.count_created_since_with_status(
            today_start, "pending_payment"
        )
        awaiting_odoo_sync = self.orders.count_paid_not_synced()
        failed_odoo_sync = self.outbox.count_by_type_and_status("order.paid", "failed")
        failed_notifications = self.outbox.count_by_type_and_status("order.notify", "failed")
        stuck_orders = self.orders.count_stuck(stuck_threshold)
        payment_incomplete = self.orders.count_payment_incomplete(payment_incomplete_threshold)

        return DashboardSummary(
            orders_today=orders_today,
            revenue_today=revenue_today,
            paid_orders_today=paid_orders_today,
            pending_payment_orders_today=pending_payment_orders_today,
            awaiting_odoo_sync=awaiting_odoo_sync,
            failed_odoo_sync=failed_odoo_sync,
            failed_notifications=failed_notifications,
            stuck_orders=stuck_orders,
            orders_requiring_attention=(
                failed_odoo_sync + failed_notifications + stuck_orders + payment_incomplete
            ),
        )

    def recent_orders(self, limit: int = 10) -> list[Order]:
        return list(self.orders.list_recent(limit))

    def alerts(self, *, now: datetime | None = None) -> list[DashboardAlert]:
        now = now or datetime.now(UTC)
        stuck_threshold = now - timedelta(minutes=self.settings.ops_stuck_order_minutes)
        payment_incomplete_threshold = stuck_threshold

        alerts: list[DashboardAlert] = []
        failed_sync = self.outbox.count_by_type_and_status("order.paid", "failed")
        if failed_sync:
            alerts.append(
                DashboardAlert(
                    type="failed_odoo_sync",
                    message="Orders failed to sync to Odoo and need a retry.",
                    count=failed_sync,
                )
            )

        failed_notify = self.outbox.count_by_type_and_status("order.notify", "failed")
        if failed_notify:
            alerts.append(
                DashboardAlert(
                    type="failed_notifications",
                    message="Order confirmations failed to send and need a retry.",
                    count=failed_notify,
                )
            )

        stuck = self.orders.count_stuck(stuck_threshold)
        if stuck:
            alerts.append(
                DashboardAlert(
                    type="stuck_orders",
                    message=(
                        f"Orders have shown no progress for over "
                        f"{self.settings.ops_stuck_order_minutes} minutes."
                    ),
                    count=stuck,
                )
            )

        payment_incomplete = self.orders.count_payment_incomplete(payment_incomplete_threshold)
        if payment_incomplete:
            alerts.append(
                DashboardAlert(
                    type="payment_incomplete",
                    message="Orders were created but payment was never completed.",
                    count=payment_incomplete,
                )
            )

        awaiting_sync = self.orders.count_paid_not_synced()
        if awaiting_sync:
            alerts.append(
                DashboardAlert(
                    type="awaiting_odoo_sync",
                    message="Paid orders are still waiting to sync to Odoo.",
                    count=awaiting_sync,
                )
            )

        return alerts
