"""Endpoint-level tests for POST /api/v1/orders/{id}/pay — same TestClient +
savepoint-isolated db_session pattern as test_orders_api.py.
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.models.orders.order_payment import OrderPayment
from tests.integration.catalogue_factories import make_product_with_default_variant


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _create_pending_order(api_client: TestClient, db_session: Session) -> dict:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    payload = {
        "items": [{"product_slug": product.slug, "quantity": 1}],
        "promo_code": None,
        "customer": {"name": "Sara M.", "email": "sara@example.com", "phone": "+966500000000"},
        "delivery": {
            "is_gift": False,
            "recipient_name": "Sara M.",
            "recipient_phone": "+966500000000",
            "area": "Al Olaya",
            "address": "123 Test Street",
            "delivery_date": "Tomorrow",
            "delivery_time": "10:00am - 12:00pm",
        },
    }
    response = api_client.post("/api/v1/orders", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_pay_order_transitions_pending_payment_to_paid(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_pending_order(api_client, db_session)

    response = api_client.post(
        f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Credit / Debit Card"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paid"


def test_pay_order_response_includes_payment_method_and_status_history(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_pending_order(api_client, db_session)

    body = api_client.post(
        f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Apple Pay"}
    ).json()

    assert body["payment_method"] == "Apple Pay"
    statuses = [event["status"] for event in body["status_history"]]
    assert statuses == ["pending_payment", "paid"]


def test_pay_order_records_a_payment_row(api_client: TestClient, db_session: Session) -> None:
    order = _create_pending_order(api_client, db_session)

    api_client.post(f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Apple Pay"})

    payments = (
        db_session.execute(select(OrderPayment).where(OrderPayment.order_id == order["id"]))
        .scalars()
        .all()
    )
    assert len(payments) == 1
    assert payments[0].status == "succeeded"
    assert payments[0].provider == "stub"
    assert payments[0].method_label == "Apple Pay"
    assert payments[0].provider_reference.startswith("stub_")


def test_pay_order_enqueues_an_order_paid_outbox_event(
    api_client: TestClient, db_session: Session
) -> None:
    order = _create_pending_order(api_client, db_session)

    api_client.post(f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Cash on Delivery"})

    events = (
        db_session.execute(
            select(OrderOutboxEvent).where(
                OrderOutboxEvent.order_id == order["id"],
                OrderOutboxEvent.event_type == "order.paid",
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].status == "pending"


def test_pay_order_twice_is_rejected_with_409(api_client: TestClient, db_session: Session) -> None:
    order = _create_pending_order(api_client, db_session)
    first = api_client.post(f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Cash"})
    assert first.status_code == 200

    second = api_client.post(f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Cash"})

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_pay_unknown_order_404s(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/orders/00000000-0000-0000-0000-000000000000/pay",
        json={"method_label": "Cash"},
    )

    assert response.status_code == 404
