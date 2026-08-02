"""Endpoint-level tests for POST/GET /api/v1/orders — exercises the real FastAPI app
via TestClient, with `get_db` overridden to reuse the test's savepoint-isolated
`db_session` (same pattern as test_catalogue_api.py).
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
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
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


def _checkout_payload(
    *product_slugs_and_qty: tuple[str, int], promo_code: str | None = None
) -> dict:
    return {
        "items": [{"product_slug": slug, "quantity": qty} for slug, qty in product_slugs_and_qty],
        "promo_code": promo_code,
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


def test_create_order_prices_and_persists(api_client: TestClient, db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))

    response = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1)))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "pending_payment"
    assert body["subtotal_amount"] == "50.00"
    assert body["order_number"].startswith("TB-")
    assert body["tracking_token"].startswith("tk-")
    assert len(body["items"]) == 1
    assert body["items"][0]["sku"] == product.sku


def test_create_order_writes_order_and_outbox_event_in_one_transaction(
    api_client: TestClient, db_session: Session
) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))

    response = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1)))
    order_id = response.json()["id"]

    order = db_session.get(Order, order_id)
    assert order is not None

    outbox_events = (
        db_session.execute(select(OrderOutboxEvent).where(OrderOutboxEvent.order_id == order.id))
        .scalars()
        .all()
    )
    assert len(outbox_events) == 1
    assert outbox_events[0].event_type == "order.created"
    assert outbox_events[0].status == "pending"


def test_create_order_rejects_unknown_product_with_404(
    api_client: TestClient, db_session: Session
) -> None:
    response = api_client.post("/api/v1/orders", json=_checkout_payload(("does-not-exist", 1)))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_create_order_rejects_below_minimum_order_with_422(
    api_client: TestClient, db_session: Session
) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("5.00"))

    response = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1)))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_order_rejects_empty_cart_with_422(api_client: TestClient) -> None:
    payload = _checkout_payload()

    response = api_client.post("/api/v1/orders", json=payload)

    assert response.status_code == 422


def test_get_order_by_id_returns_full_shape(api_client: TestClient, db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    created = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1))).json()

    response = api_client.get(f"/api/v1/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json()["order_number"] == created["order_number"]


def test_get_order_by_id_404_for_missing_order(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_get_order_by_tracking_token(api_client: TestClient, db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    created = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1))).json()

    response = api_client.get(f"/api/v1/orders/by-tracking-token/{created['tracking_token']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_order_by_tracking_token_404_for_unknown_token(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/orders/by-tracking-token/tk-doesnotexist")

    assert response.status_code == 404
