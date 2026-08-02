from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardSummaryOut(BaseModel):
    orders_today: int
    revenue_today: str
    paid_orders_today: int
    pending_payment_orders_today: int
    awaiting_odoo_sync: int
    failed_odoo_sync: int
    failed_notifications: int
    stuck_orders: int
    orders_requiring_attention: int


class DashboardRecentOrderOut(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_phone: str
    total_amount: str
    payment_status: str
    status: str
    odoo_sync_status: str
    created_at: datetime


class DashboardAlertOut(BaseModel):
    type: str
    message: str
    count: int
