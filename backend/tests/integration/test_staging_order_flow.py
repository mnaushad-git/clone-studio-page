"""On staging, a checkout paid by the stub is a real test order: it is not marked demo, its
order.paid outbox event commits with the payment, and the worker pushes it to the staging Odoo
exactly once, retrying a failure. The pusher here stands in for LiveOdooOrderPusher, whose Odoo
calls are covered in tests/unit/odoo and whose staging target checks are covered in
tests/unit/test_staging_settings.py."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import STAGING_ODOO_BASE_URL, STAGING_ODOO_DATABASE, Settings
from app.dependencies import get_db
from app.integrations.odoo.order_push import OdooPushResult
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_payment import OrderPayment
from app.services.checkout import odoo_sync_service as sync_module
from app.services.checkout import order_service, payment_service
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
from tests.integration.catalogue_factories import make_product_with_default_variant


def _staging_api() -> Settings:
    return Settings(
        _env_file=None,
        deployment_stage="staging",
        service_role="api",
        odoo_order_push_provider="live",
        odoo_base_url=STAGING_ODOO_BASE_URL,
        odoo_database=STAGING_ODOO_DATABASE,
    )


class _RecordingPusher:
    name = "live"

    def __init__(self, *results: bool) -> None:
        self.results = list(results)
        self.pushed: list[str] = []

    def push_order(self, *, order_number: str, **_: Any) -> OdooPushResult:
        self.pushed.append(order_number)
        ok = self.results.pop(0)
        return OdooPushResult(success=ok, odoo_sale_order_id=4242 if ok else None, raw={})


@pytest.fixture
def staging(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _staging_api()
    monkeypatch.setattr(order_service, "get_settings", lambda: settings)
    monkeypatch.setattr(payment_service, "get_settings", lambda: settings)
    monkeypatch.setattr("app.api.v1.endpoints.orders.push_paid_orders_to_odoo.delay", lambda: None)
    monkeypatch.setattr("app.api.v1.endpoints.orders.send_order_confirmations.delay", lambda: None)


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _checkout(client: TestClient, session: Session) -> dict[str, Any]:
    product = make_product_with_default_variant(session, amount=Decimal("50.00"))
    contact = {"name": "Staging Tester", "phone": "+966500000001"}
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": None,
            "customer": contact,
            "delivery": {
                "is_gift": False,
                "recipient_name": contact["name"],
                "recipient_phone": contact["phone"],
                "area": "Al Olaya",
                "address": "1 Test Street",
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _pay(client: TestClient, order_id: str) -> Any:
    # The label the frontend sends when built with VITE_DEMO_MODE=true.
    return client.post(
        f"/api/v1/orders/{order_id}/pay", json={"method_label": "Demo payment (Card)"}
    )


def _paid_event(session: Session, order_id: str) -> OrderOutboxEvent:
    return session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.event_type == "order.paid"
        )
    ).scalar_one()


def _use(monkeypatch: pytest.MonkeyPatch, pusher: _RecordingPusher) -> None:
    monkeypatch.setattr(sync_module, "get_odoo_order_pusher", lambda settings: pusher)


def test_a_staging_order_is_a_real_order_paid_by_the_stub(
    api_client: TestClient, db_session: Session, staging: None
) -> None:
    created = _checkout(api_client, db_session)
    assert created["is_demo"] is False
    assert created["order_number"].startswith("TB-")

    paid = _pay(api_client, created["id"])

    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    payment = db_session.execute(
        select(OrderPayment).where(OrderPayment.order_id == created["id"])
    ).scalar_one()
    assert payment.provider == "stub"
    assert _paid_event(db_session, created["id"]).status == "pending"


def test_a_paid_staging_order_reaches_the_staging_odoo_exactly_once(
    api_client: TestClient,
    db_session: Session,
    staging: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _checkout(api_client, db_session)
    _pay(api_client, created["id"])
    pusher = _RecordingPusher(True)
    _use(monkeypatch, pusher)
    service = OdooOrderSyncService(db_session)

    assert service.sync_paid_orders().succeeded == 1
    assert service.sync_paid_orders().processed == 0

    assert pusher.pushed == [created["order_number"]]
    order = db_session.get(Order, created["id"])
    assert order is not None
    assert (order.odoo_sync_status, order.odoo_sale_order_id) == ("synced", 4242)
    assert _paid_event(db_session, created["id"]).status == "completed"


def test_a_failed_staging_push_is_retried_and_then_synced(
    api_client: TestClient,
    db_session: Session,
    staging: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _checkout(api_client, db_session)
    _pay(api_client, created["id"])
    pusher = _RecordingPusher(False, True)
    _use(monkeypatch, pusher)
    service = OdooOrderSyncService(db_session)

    service.sync_paid_orders()
    event = _paid_event(db_session, created["id"])
    assert event.status == "failed"
    event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    assert service.sync_paid_orders().succeeded == 1
    assert pusher.pushed == [created["order_number"]] * 2
    order = db_session.get(Order, created["id"])
    assert order is not None
    assert order.odoo_sync_status == "synced"


def test_a_staging_order_cannot_be_paid_twice_or_queued_twice(
    api_client: TestClient, db_session: Session, staging: None
) -> None:
    created = _checkout(api_client, db_session)
    assert _pay(api_client, created["id"]).status_code == 200

    assert _pay(api_client, created["id"]).status_code == 409
    _paid_event(db_session, created["id"])  # exactly one, or scalar_one() raises
