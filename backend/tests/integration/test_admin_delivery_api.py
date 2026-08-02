"""Endpoint-level tests for /api/v1/admin/delivery-settings and
/api/v1/admin/delivery-slots (task brief §12)."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from tests.integration.admin_factories import login_as, make_admin_user
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


def test_get_delivery_settings(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/delivery-settings")

    assert response.status_code == 200
    body = response.json()
    assert "flat_delivery_fee" in body
    assert "available_days" in body


def test_update_delivery_settings_takes_effect_on_next_checkout(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.patch(
        "/api/v1/admin/delivery-settings",
        json={"flat_delivery_fee": 42.5, "free_delivery_threshold": 0},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    assert response.json()["flat_delivery_fee"] == "42.50"

    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))
    order_response = api_client.post(
        "/api/v1/orders",
        json={
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
                "delivery_time": None,
            },
        },
    )
    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["delivery_fee_amount"] == "42.50"


def test_disabling_delivery_blocks_checkout(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    api_client.patch(
        "/api/v1/admin/delivery-settings",
        json={"delivery_enabled": False},
        headers={"X-CSRF-Token": csrf},
    )

    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))
    response = api_client.post(
        "/api/v1/orders",
        json={
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
                "delivery_time": None,
            },
        },
    )

    assert response.status_code == 422


def test_create_and_list_delivery_slot(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)

    create_response = api_client.post(
        "/api/v1/admin/delivery-slots",
        json={"label": "Late Night", "start_time": "22:00", "end_time": "23:00"},
        headers={"X-CSRF-Token": csrf},
    )
    assert create_response.status_code == 200, create_response.text
    slot_id = create_response.json()["id"]

    list_response = api_client.get("/api/v1/admin/delivery-slots")
    labels = [s["label"] for s in list_response.json()]
    assert "Late Night" in labels

    delete_response = api_client.delete(
        f"/api/v1/admin/delivery-slots/{slot_id}", headers={"X-CSRF-Token": csrf}
    )
    assert delete_response.status_code == 204


def test_disabled_slot_rejected_at_checkout(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    create_response = api_client.post(
        "/api/v1/admin/delivery-slots",
        json={
            "label": "Disabled Slot",
            "start_time": "23:00",
            "end_time": "23:30",
            "active": False,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert create_response.status_code == 200

    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))
    response = api_client.post(
        "/api/v1/orders",
        json={
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
                "delivery_time": "Disabled Slot",
            },
        },
    )

    assert response.status_code == 422
