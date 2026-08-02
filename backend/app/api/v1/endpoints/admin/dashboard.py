"""Admin dashboard endpoints (task brief §4). OPERATIONS_ADMIN and SUPER_ADMIN only —
CATALOGUE_ADMIN/SUPPORT_ADMIN have no dashboard use case in this MVP's scope."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.admin_auth import require_role
from app.api.v1.schemas.admin_dashboard import (
    DashboardAlertOut,
    DashboardRecentOrderOut,
    DashboardSummaryOut,
)
from app.dependencies import get_db
from app.services.admin.dashboard_service import DashboardService
from app.services.admin.order_admin_service import payment_status_for

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])

_ALLOWED_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN")


def _money(amount: object) -> str:
    return f"{float(amount):.2f}"  # type: ignore[arg-type]


@router.get("/summary", dependencies=[Depends(require_role(*_ALLOWED_ROLES))])
def get_summary(session: Session = Depends(get_db)) -> DashboardSummaryOut:
    summary = DashboardService(session).summary()
    return DashboardSummaryOut(
        orders_today=summary.orders_today,
        revenue_today=_money(summary.revenue_today),
        paid_orders_today=summary.paid_orders_today,
        pending_payment_orders_today=summary.pending_payment_orders_today,
        awaiting_odoo_sync=summary.awaiting_odoo_sync,
        failed_odoo_sync=summary.failed_odoo_sync,
        failed_notifications=summary.failed_notifications,
        stuck_orders=summary.stuck_orders,
        orders_requiring_attention=summary.orders_requiring_attention,
    )


@router.get("/recent-orders", dependencies=[Depends(require_role(*_ALLOWED_ROLES))])
def get_recent_orders(session: Session = Depends(get_db)) -> list[DashboardRecentOrderOut]:
    orders = DashboardService(session).recent_orders(limit=10)
    return [
        DashboardRecentOrderOut(
            id=str(order.id),
            order_number=order.order_number,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            total_amount=_money(order.total_amount),
            payment_status=payment_status_for(order),
            status=order.status,
            odoo_sync_status=order.odoo_sync_status,
            created_at=order.created_at,
        )
        for order in orders
    ]


@router.get("/operational-alerts", dependencies=[Depends(require_role(*_ALLOWED_ROLES))])
def get_operational_alerts(session: Session = Depends(get_db)) -> list[DashboardAlertOut]:
    alerts = DashboardService(session).alerts()
    return [
        DashboardAlertOut(type=alert.type, message=alert.message, count=alert.count)
        for alert in alerts
    ]
