"""A stub payment must never mark a real order paid, and a real provider must never charge a
demo order, whichever stage the deployment is running in."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.dependencies import get_db
from app.integrations.payments.base import PaymentResult
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_payment import OrderPayment
from app.services.admin.order_admin_service import ORDER_STATUS_TRANSITIONS
from app.services.checkout import order_service, payment_service
from tests.integration.test_orders_api import _checkout_payload, make_product_with_default_variant

LIVE_SETTINGS: dict[str, Any] = {
    "deployment_stage": "live",
    "payment_provider": "real_gateway",
    "notification_provider": "real_sender",
    "odoo_order_push_provider": "live",
    "finance_rules_approved": True,
}


class RecordingRealProvider:
    name = "real_gateway"

    def __init__(self) -> None:
        self.charged: list[str] = []

    def charge(self, *, order_number: str, **_: Any) -> PaymentResult:
        self.charged.append(order_number)
        return PaymentResult(success=True, status="succeeded", provider_reference="r1", raw={})


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def no_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.orders.push_paid_orders_to_odoo.delay", lambda: None)
    monkeypatch.setattr("app.api.v1.endpoints.orders.send_order_confirmations.delay", lambda: None)


def _create_order(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    demo: bool,
) -> dict[str, Any]:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    stage = "demo" if demo else "development"
    with monkeypatch.context() as patch:
        patch.setattr(order_service, "get_settings", lambda: Settings(deployment_stage=stage))
        response = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1)))
    assert response.status_code == 200, response.text
    assert response.json()["is_demo"] is demo
    return response.json()


def _pay(api_client: TestClient, order_id: str) -> Any:
    return api_client.post(f"/api/v1/orders/{order_id}/pay", json={"method_label": "Card"})


def _assert_nothing_happened(db_session: Session, order_id: str) -> None:
    db_session.expire_all()
    order = db_session.get(Order, order_id)
    assert order is not None
    assert order.status == "pending_payment"
    payments = db_session.execute(select(OrderPayment).where(OrderPayment.order_id == order_id))
    assert payments.scalars().all() == []
    events = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order_id,
            OrderOutboxEvent.event_type.in_(("order.paid", "order.notify")),
        )
    )
    assert events.scalars().all() == []


def test_demo_stage_refuses_to_mark_a_real_order_paid(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_order(api_client, db_session, monkeypatch, demo=False)
    monkeypatch.setattr(payment_service, "get_settings", lambda: Settings(deployment_stage="demo"))

    response = _pay(api_client, order["id"])

    assert response.status_code == 409
    _assert_nothing_happened(db_session, order["id"])


def test_demo_stage_can_pay_a_demo_order(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_order(api_client, db_session, monkeypatch, demo=True)
    monkeypatch.setattr(payment_service, "get_settings", lambda: Settings(deployment_stage="demo"))

    response = _pay(api_client, order["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_real_provider_refuses_a_demo_order_without_charging(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_order(api_client, db_session, monkeypatch, demo=True)
    provider = RecordingRealProvider()
    monkeypatch.setattr(payment_service, "get_settings", lambda: Settings(**LIVE_SETTINGS))
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda _settings: provider)

    response = _pay(api_client, order["id"])

    assert response.status_code == 409
    assert provider.charged == []
    _assert_nothing_happened(db_session, order["id"])


def test_real_provider_charges_a_real_order(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_order(api_client, db_session, monkeypatch, demo=False)
    provider = RecordingRealProvider()
    monkeypatch.setattr(payment_service, "get_settings", lambda: Settings(**LIVE_SETTINGS))
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda _settings: provider)

    response = _pay(api_client, order["id"])

    assert response.status_code == 200
    assert provider.charged == [order["order_number"]]


def test_a_paid_order_cannot_be_paid_again(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _create_order(api_client, db_session, monkeypatch, demo=True)
    monkeypatch.setattr(payment_service, "get_settings", lambda: Settings(deployment_stage="demo"))
    assert _pay(api_client, order["id"]).status_code == 200

    assert _pay(api_client, order["id"]).status_code == 409


def test_unknown_order_cannot_be_paid(api_client: TestClient) -> None:
    response = _pay(api_client, "00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_admin_status_changes_can_never_set_an_order_to_paid() -> None:
    assert all("paid" not in targets for targets in ORDER_STATUS_TRANSITIONS.values())
