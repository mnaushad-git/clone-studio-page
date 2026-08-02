"""OdooOrderSyncService against a real order created+paid through the actual API, so
these tests exercise the same outbox rows the endpoints produce, not hand-built ones.
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.integrations.odoo.order_push import OdooPushResult
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.services.checkout import odoo_sync_service as odoo_sync_service_module
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
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


def _create_and_pay_order(api_client: TestClient, db_session: Session) -> dict:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    created = api_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": None,
            "customer": {"name": "Sara M.", "phone": "+966500000000"},
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


def test_sync_paid_orders_marks_order_and_outbox_event_synced(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_and_pay_order(api_client, db_session)

    summary = OdooOrderSyncService(db_session).sync_paid_orders()

    assert summary.processed == 1
    assert summary.succeeded == 1
    assert summary.failed == 0

    db_order = db_session.get(Order, order["id"])
    assert db_order is not None
    assert db_order.odoo_sync_status == "synced"
    assert db_order.odoo_last_synced_at is not None

    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"],
            OrderOutboxEvent.event_type == "order.paid",
        )
    ).scalar_one()
    assert event.status == "completed"
    assert event.processed_at is not None


def test_sync_paid_orders_is_a_no_op_when_nothing_is_pending(db_session: Session) -> None:
    summary = OdooOrderSyncService(db_session).sync_paid_orders()

    assert summary == type(summary)(processed=0, succeeded=0, failed=0)


def test_a_failing_push_marks_the_event_failed_and_stays_retryable(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_and_pay_order(api_client, db_session)

    class _AlwaysFailsPusher:
        name = "stub"

        def push_order(self, **kwargs: object) -> OdooPushResult:
            return OdooPushResult(success=False, odoo_sale_order_id=None, raw={})

    monkeypatch.setattr(
        odoo_sync_service_module, "get_odoo_order_pusher", lambda settings: _AlwaysFailsPusher()
    )

    summary = OdooOrderSyncService(db_session).sync_paid_orders()

    assert summary.succeeded == 0
    assert summary.failed == 1

    db_order = db_session.get(Order, order["id"])
    assert db_order is not None
    assert db_order.odoo_sync_status == "failed"

    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"],
            OrderOutboxEvent.event_type == "order.paid",
        )
    ).scalar_one()
    # "failed", not "completed" — still eligible for a future retry pass, never
    # silently dropped.
    assert event.status == "failed"
    assert event.attempts == 1


def test_an_exception_from_the_pusher_is_caught_and_recorded_not_raised(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_and_pay_order(api_client, db_session)

    class _RaisingPusher:
        name = "stub"

        def push_order(self, **kwargs: object) -> OdooPushResult:
            raise RuntimeError("Odoo instance unreachable")

    monkeypatch.setattr(
        odoo_sync_service_module, "get_odoo_order_pusher", lambda settings: _RaisingPusher()
    )

    summary = OdooOrderSyncService(db_session).sync_paid_orders()

    assert summary.failed == 1
    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"],
            OrderOutboxEvent.event_type == "order.paid",
        )
    ).scalar_one()
    assert event.status == "failed"
    assert "unreachable" in (event.last_error or "")
