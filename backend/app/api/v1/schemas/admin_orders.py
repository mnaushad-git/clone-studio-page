"""Pydantic models for /api/v1/admin/orders/* and /api/v1/admin/dashboard/*."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminOrderListItemOut(BaseModel):
    id: str
    order_number: str
    created_at: datetime
    customer_name: str
    customer_phone: str
    delivery_date: str | None
    delivery_time: str | None
    item_count: int
    items_summary: list[str]
    subtotal_amount: str
    delivery_fee_amount: str
    discount_amount: str
    total_amount: str
    payment_status: str
    status: str
    odoo_sync_status: str
    notification_status: str


class AdminOrderListOut(BaseModel):
    items: list[AdminOrderListItemOut]
    total: int
    limit: int
    offset: int


class AdminOrderItemAttributeOut(BaseModel):
    """Snapshot of one selected axis, taken at order-creation time — mirrors
    app/api/v1/schemas/catalogue.py's VariantAttributeOut (duplicated, not shared, per
    this codebase's convention of small per-schema-file DTOs)."""

    code: str
    name_en: str
    value_label_en: str


class AdminOrderItemOut(BaseModel):
    id: str
    sku: str
    name_en: str
    attributes: list[AdminOrderItemAttributeOut]
    inscription: str | None
    quantity: int
    unit_price: str
    line_total: str


class AdminOrderPaymentOut(BaseModel):
    id: str
    attempt_number: int
    provider: str
    method_label: str
    amount: str
    currency: str
    status: str
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime


class AdminOrderNotificationOut(BaseModel):
    id: str
    channel: str
    template: str
    recipient: str
    provider: str
    status: str
    provider_reference: str | None
    created_at: datetime


class AdminOrderOutboxEventOut(BaseModel):
    id: str
    event_type: str
    status: str
    attempts: int
    last_error: str | None
    processed_at: datetime | None
    created_at: datetime


class AdminOrderStatusEventOut(BaseModel):
    status: str
    note: str | None
    occurred_at: datetime


class AdminAuditEventBriefOut(BaseModel):
    id: str
    admin_email: str
    action: str
    reason: str | None
    created_at: datetime


class AdminOrderCustomerOut(BaseModel):
    name: str
    email: str | None
    phone: str


class AdminOrderDeliveryOut(BaseModel):
    recipient_name: str
    recipient_phone: str
    area: str | None
    address: str | None
    address_extra: str | None
    delivery_date: str | None
    delivery_time: str | None
    is_gift: bool
    identity_secret: bool


class AdminOrderOdooOut(BaseModel):
    sync_status: str
    sale_order_id: int | None
    last_synced_at: datetime | None
    outbox_events: list[AdminOrderOutboxEventOut]


class AdminOrderDetailOut(BaseModel):
    id: str
    order_number: str
    status: str
    payment_status: str
    currency: str
    subtotal_amount: str
    discount_amount: str
    promo_code: str | None
    discount_type: str | None
    discount_value: str | None
    tax_amount: str
    delivery_fee_amount: str
    total_amount: str
    cancellation_reason: str | None
    refund_status: str | None
    tracking_token: str
    created_at: datetime
    updated_at: datetime
    customer: AdminOrderCustomerOut
    delivery: AdminOrderDeliveryOut
    items: list[AdminOrderItemOut]
    payments: list[AdminOrderPaymentOut]
    odoo: AdminOrderOdooOut
    notifications: list[AdminOrderNotificationOut]
    notification_outbox_events: list[AdminOrderOutboxEventOut]
    status_history: list[AdminOrderStatusEventOut]
    audit_events: list[AdminAuditEventBriefOut]


class AdminOrderStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=500)


class AdminRetryResponseOut(BaseModel):
    queued: bool
    worker_dispatched: bool
    message: str
