"""NotificationService against a real order created+paid through the actual API —
mirrors test_odoo_sync_service.py's structure (same rationale: exercise the real
outbox rows the endpoints produce, not hand-built ones).
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.integrations.notifications.base import NotificationResult
from app.main import app
from app.models.orders.order_notification import OrderNotification
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.services.checkout import notification_service as notification_service_module
from app.services.checkout.notification_service import NotificationService
from tests.integration.catalogue_factories import make_product_with_default_variant


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _create_and_pay_order(
    api_client: TestClient, db_session: Session, *, customer_email: str | None
) -> dict:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    customer: dict[str, str] = {"name": "Sara M.", "phone": "+966500000000"}
    if customer_email is not None:
        customer["email"] = customer_email
    created = api_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": None,
            "customer": customer,
            "delivery": {
                "is_gift": False,
                "recipient_name": "Sara M.",
                "recipient_phone": "+966500000000",
                "area": "Al Olaya",
                "address": "123 Test Street",
            },
        },
    ).json()
    paid = api_client.post(
        f"/api/v1/orders/{created['id']}/pay", json={"method_label": "Cash"}
    ).json()
    return paid


def _notify_event(db_session: Session, order_id: str) -> OrderOutboxEvent:
    return db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.event_type == "order.notify"
        )
    ).scalar_one()


def test_send_pending_confirmations_sends_both_channels_when_email_present(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_and_pay_order(api_client, db_session, customer_email="sara@example.com")

    summary = NotificationService(db_session).send_pending_confirmations()

    assert summary.processed == 1
    assert summary.succeeded == 1
    assert summary.failed == 0

    notifications = (
        db_session.execute(
            select(OrderNotification).where(OrderNotification.order_id == order["id"])
        )
        .scalars()
        .all()
    )
    channels = {n.channel for n in notifications}
    assert channels == {"email", "sms"}
    assert all(n.status == "sent" for n in notifications)

    event = _notify_event(db_session, order["id"])
    assert event.status == "completed"
    assert event.processed_at is not None


def test_send_pending_confirmations_skips_email_when_no_customer_email(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_and_pay_order(api_client, db_session, customer_email=None)

    summary = NotificationService(db_session).send_pending_confirmations()

    assert summary.succeeded == 1
    notifications = (
        db_session.execute(
            select(OrderNotification).where(OrderNotification.order_id == order["id"])
        )
        .scalars()
        .all()
    )
    channels = {n.channel for n in notifications}
    assert channels == {"sms"}


def test_send_pending_confirmations_is_a_no_op_when_nothing_is_pending(
    db_session: Session,
) -> None:
    summary = NotificationService(db_session).send_pending_confirmations()

    assert summary == type(summary)(processed=0, succeeded=0, failed=0)


def test_a_failing_sms_send_marks_the_event_failed_and_stays_retryable(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_and_pay_order(api_client, db_session, customer_email="sara@example.com")

    class _SmsFailsProvider:
        name = "stub"

        def send_email(self, **kwargs: object) -> NotificationResult:
            return NotificationResult(success=True, status="sent", provider_reference="ok", raw={})

        def send_sms(self, **kwargs: object) -> NotificationResult:
            return NotificationResult(
                success=False, status="failed", provider_reference="fail", raw={}
            )

    monkeypatch.setattr(
        notification_service_module,
        "get_notification_provider",
        lambda settings: _SmsFailsProvider(),
    )

    summary = NotificationService(db_session).send_pending_confirmations()

    assert summary.failed == 1
    event = _notify_event(db_session, order["id"])
    assert event.status == "failed"
    assert event.attempts == 1


def test_an_exception_from_the_provider_is_caught_and_recorded_not_raised(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_and_pay_order(api_client, db_session, customer_email=None)

    class _RaisingProvider:
        name = "stub"

        def send_email(self, **kwargs: object) -> NotificationResult:
            raise AssertionError("should not be called — no customer email on this order")

        def send_sms(self, **kwargs: object) -> NotificationResult:
            raise RuntimeError("SMS gateway unreachable")

    monkeypatch.setattr(
        notification_service_module,
        "get_notification_provider",
        lambda settings: _RaisingProvider(),
    )

    summary = NotificationService(db_session).send_pending_confirmations()

    assert summary.failed == 1
    event = _notify_event(db_session, order["id"])
    assert event.status == "failed"
    assert "unreachable" in (event.last_error or "")


def test_pay_order_enqueues_a_distinct_order_notify_event_from_order_paid(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_and_pay_order(api_client, db_session, customer_email="sara@example.com")

    events = (
        db_session.execute(select(OrderOutboxEvent).where(OrderOutboxEvent.order_id == order["id"]))
        .scalars()
        .all()
    )
    # order.created comes from OrderService.create_order; order.paid and order.notify
    # both come from PaymentService.pay_order — two distinct rows, not one shared one
    # (see payment_service.py's docstring for why that distinction matters).
    event_types = sorted(e.event_type for e in events)
    assert event_types == ["order.created", "order.notify", "order.paid"]
