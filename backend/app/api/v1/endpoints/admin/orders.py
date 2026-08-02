"""Admin order endpoints (task brief §5-8). Role matrix (plan "Key decisions" §2):
SUPER_ADMIN/OPERATIONS_ADMIN — full order operations, including status changes and
both retry types. SUPPORT_ADMIN — read-only order/notification visibility plus
notification retry only; no status changes, no payment visibility, no Odoo-sync
retry (financial/sync operations stay with OPERATIONS_ADMIN+).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import require_csrf, require_role
from app.api.v1.schemas.admin_orders import (
    AdminAuditEventBriefOut,
    AdminOrderCustomerOut,
    AdminOrderDeliveryOut,
    AdminOrderDetailOut,
    AdminOrderItemAttributeOut,
    AdminOrderItemOut,
    AdminOrderListItemOut,
    AdminOrderListOut,
    AdminOrderNotificationOut,
    AdminOrderOdooOut,
    AdminOrderOutboxEventOut,
    AdminOrderPaymentOut,
    AdminOrderStatusEventOut,
    AdminOrderStatusUpdateRequest,
    AdminRetryResponseOut,
)
from app.core.exceptions import NotFoundError
from app.dependencies import get_db
from app.models.admin.admin_user import AdminUser
from app.models.orders.order import Order
from app.models.orders.order_item import OrderItem
from app.models.orders.order_notification import OrderNotification
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_payment import OrderPayment
from app.repositories.admin.admin_audit_repository import AdminAuditRepository
from app.repositories.orders.order_payment_repository import OrderPaymentRepository
from app.services.admin.order_admin_service import OrderAdminService, payment_status_for

router = APIRouter(prefix="/orders", tags=["admin-orders"])

_VIEW_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN", "SUPPORT_ADMIN")
_OPERATE_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN")
_FINANCIAL_VIEW_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN")


def _money(amount: object) -> str:
    return f"{float(amount):.2f}"  # type: ignore[arg-type]


def _notification_status(order: Order) -> str:
    statuses = {n.status for n in order.notifications}
    if "failed" in statuses:
        return "failed"
    if "sent" in statuses:
        return "sent"
    return "none"


def _item_summary(item: OrderItem) -> str:
    variant = " · ".join(a["value_label_en"] for a in (item.attributes_json or []))
    suffix = f" ({variant})" if variant else ""
    return f"{item.quantity}× {item.name_en}{suffix}"


def _list_item_out(order: Order) -> AdminOrderListItemOut:
    return AdminOrderListItemOut(
        id=str(order.id),
        order_number=order.order_number,
        created_at=order.created_at,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        delivery_date=order.delivery_date,
        delivery_time=order.delivery_time,
        item_count=len(order.items),
        items_summary=[_item_summary(it) for it in order.items],
        subtotal_amount=_money(order.subtotal_amount),
        delivery_fee_amount=_money(order.delivery_fee_amount),
        discount_amount=_money(order.discount_amount),
        total_amount=_money(order.total_amount),
        payment_status=payment_status_for(order),
        status=order.status,
        odoo_sync_status=order.odoo_sync_status,
        notification_status=_notification_status(order),
    )


def _payment_out(payment: OrderPayment, attempt_number: int) -> AdminOrderPaymentOut:
    return AdminOrderPaymentOut(
        id=str(payment.id),
        attempt_number=attempt_number,
        provider=payment.provider,
        method_label=payment.method_label,
        amount=_money(payment.amount),
        currency=payment.currency,
        status=payment.status,
        provider_reference=payment.provider_reference,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


def _notification_out(notification: OrderNotification) -> AdminOrderNotificationOut:
    return AdminOrderNotificationOut(
        id=str(notification.id),
        channel=notification.channel,
        template=notification.template,
        recipient=notification.recipient,
        provider=notification.provider,
        status=notification.status,
        provider_reference=notification.provider_reference,
        created_at=notification.created_at,
    )


def _outbox_out(event: OrderOutboxEvent) -> AdminOrderOutboxEventOut:
    return AdminOrderOutboxEventOut(
        id=str(event.id),
        event_type=event.event_type,
        status=event.status,
        attempts=event.attempts,
        last_error=event.last_error,
        processed_at=event.processed_at,
        created_at=event.created_at,
    )


def _detail_out(order: Order, audit_repo: AdminAuditRepository) -> AdminOrderDetailOut:
    payments_sorted = sorted(order.payments, key=lambda p: p.created_at)
    odoo_events = [e for e in order.outbox_events if e.event_type == "order.paid"]
    notify_events = [e for e in order.outbox_events if e.event_type == "order.notify"]
    audit_events, _ = audit_repo.search(entity_type="order", entity_id=str(order.id), limit=20)

    return AdminOrderDetailOut(
        id=str(order.id),
        order_number=order.order_number,
        status=order.status,
        payment_status=payment_status_for(order),
        currency=order.currency,
        subtotal_amount=_money(order.subtotal_amount),
        discount_amount=_money(order.discount_amount),
        promo_code=order.promo_code,
        discount_type=order.discount_type,
        discount_value=(_money(order.discount_value) if order.discount_value is not None else None),
        tax_amount=_money(order.tax_amount),
        delivery_fee_amount=_money(order.delivery_fee_amount),
        total_amount=_money(order.total_amount),
        cancellation_reason=order.cancellation_reason,
        refund_status=order.refund_status,
        tracking_token=order.tracking_token,
        created_at=order.created_at,
        updated_at=order.updated_at,
        customer=AdminOrderCustomerOut(
            name=order.customer_name, email=order.customer_email, phone=order.customer_phone
        ),
        delivery=AdminOrderDeliveryOut(
            recipient_name=order.recipient_name,
            recipient_phone=order.recipient_phone,
            area=order.delivery_area,
            address=order.delivery_address,
            address_extra=order.delivery_address_extra,
            delivery_date=order.delivery_date,
            delivery_time=order.delivery_time,
            is_gift=order.is_gift,
            identity_secret=order.identity_secret,
        ),
        items=[
            AdminOrderItemOut(
                id=str(item.id),
                sku=item.sku,
                name_en=item.name_en,
                attributes=[
                    AdminOrderItemAttributeOut(**a) for a in (item.attributes_json or [])
                ],
                inscription=item.inscription,
                quantity=item.quantity,
                unit_price=_money(item.unit_price),
                line_total=_money(item.line_total),
            )
            for item in order.items
        ],
        payments=[_payment_out(p, i + 1) for i, p in enumerate(payments_sorted)],
        odoo=AdminOrderOdooOut(
            sync_status=order.odoo_sync_status,
            sale_order_id=order.odoo_sale_order_id,
            last_synced_at=order.odoo_last_synced_at,
            outbox_events=[_outbox_out(e) for e in odoo_events],
        ),
        notifications=[_notification_out(n) for n in order.notifications],
        notification_outbox_events=[_outbox_out(e) for e in notify_events],
        status_history=[
            AdminOrderStatusEventOut(status=e.status, note=e.note, occurred_at=e.occurred_at)
            for e in sorted(order.status_events, key=lambda e: e.occurred_at)
        ],
        audit_events=[
            AdminAuditEventBriefOut(
                id=str(a.id),
                admin_email=a.admin_email,
                action=a.action,
                reason=a.reason,
                created_at=a.created_at,
            )
            for a in audit_events
        ],
    )


@router.get("", dependencies=[Depends(require_role(*_VIEW_ROLES))])
def list_orders(
    session: Session = Depends(get_db),
    order_number: str | None = None,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    customer_email: str | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    odoo_sync_status: str | None = None,
    notification_status: str | None = None,
    delivery_date: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "newest",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminOrderListOut:
    items, total = OrderAdminService(session).list_orders(
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        status=status,
        payment_status=payment_status,
        odoo_sync_status=odoo_sync_status,
        notification_status=notification_status,
        delivery_date=delivery_date,
        created_from=created_from,
        created_to=created_to,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return AdminOrderListOut(
        items=[_list_item_out(o) for o in items], total=total, limit=limit, offset=offset
    )


@router.get("/{order_id}", dependencies=[Depends(require_role(*_VIEW_ROLES))])
def get_order(order_id: uuid.UUID, session: Session = Depends(get_db)) -> AdminOrderDetailOut:
    order = OrderAdminService(session).get_order_detail(order_id)
    return _detail_out(order, AdminAuditRepository(session))


@router.patch("/{order_id}/status", dependencies=[Depends(require_csrf)])
def update_order_status(
    order_id: uuid.UUID,
    body: AdminOrderStatusUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_OPERATE_ROLES)),
) -> AdminOrderDetailOut:
    OrderAdminService(session).update_status(
        order_id, body.status, note=body.note, admin=admin, request=request
    )
    session.commit()
    order = OrderAdminService(session).get_order_detail(order_id)
    return _detail_out(order, AdminAuditRepository(session))


@router.post("/{order_id}/retry-odoo-sync", dependencies=[Depends(require_csrf)])
def retry_odoo_sync(
    order_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_OPERATE_ROLES)),
) -> AdminRetryResponseOut:
    result = OrderAdminService(session).retry_odoo_sync(order_id, admin=admin, request=request)
    session.commit()
    return AdminRetryResponseOut(
        queued=result.queued, worker_dispatched=result.worker_dispatched, message=result.message
    )


@router.post("/{order_id}/retry-notification", dependencies=[Depends(require_csrf)])
def retry_notification(
    order_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role("SUPER_ADMIN", "OPERATIONS_ADMIN", "SUPPORT_ADMIN")),
) -> AdminRetryResponseOut:
    result = OrderAdminService(session).retry_notification(order_id, admin=admin, request=request)
    session.commit()
    return AdminRetryResponseOut(
        queued=result.queued, worker_dispatched=result.worker_dispatched, message=result.message
    )


@router.get("/{order_id}/payments", dependencies=[Depends(require_role(*_FINANCIAL_VIEW_ROLES))])
def get_order_payments(
    order_id: uuid.UUID, session: Session = Depends(get_db)
) -> list[AdminOrderPaymentOut]:
    order = OrderAdminService(session).get_order_detail(order_id)
    payments_sorted = sorted(order.payments, key=lambda p: p.created_at)
    return [_payment_out(p, i + 1) for i, p in enumerate(payments_sorted)]


@router.get("/{order_id}/notifications", dependencies=[Depends(require_role(*_VIEW_ROLES))])
def get_order_notifications(
    order_id: uuid.UUID, session: Session = Depends(get_db)
) -> list[AdminOrderNotificationOut]:
    order = OrderAdminService(session).get_order_detail(order_id)
    return [_notification_out(n) for n in order.notifications]


@router.get(
    "/{order_id}/outbox-events", dependencies=[Depends(require_role(*_FINANCIAL_VIEW_ROLES))]
)
def get_order_outbox_events(
    order_id: uuid.UUID, session: Session = Depends(get_db)
) -> list[AdminOrderOutboxEventOut]:
    order = OrderAdminService(session).get_order_detail(order_id)
    return [_outbox_out(e) for e in order.outbox_events]


payments_router = APIRouter(prefix="/payments", tags=["admin-orders"])


@payments_router.get("/{payment_id}", dependencies=[Depends(require_role(*_FINANCIAL_VIEW_ROLES))])
def get_payment(payment_id: uuid.UUID, session: Session = Depends(get_db)) -> AdminOrderPaymentOut:
    payment = OrderPaymentRepository(session).get_by_id(payment_id)
    if payment is None:
        raise NotFoundError(f"No payment found with id {payment_id}.")
    return _payment_out(payment, attempt_number=1)
