"""Endpoint-level tests for /api/v1/admin/orders/* and /api/v1/admin/payments/*."""

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


def _place_order(api_client: TestClient, db_session: Session, *, pay: bool = False) -> dict:
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
    order = api_client.post("/api/v1/orders", json=payload).json()
    if pay:
        order = api_client.post(
            f"/api/v1/orders/{order['id']}/pay", json={"method_label": "Cash"}
        ).json()
    return order


def test_list_orders_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/admin/orders").status_code == 401


def test_list_orders_returns_created_order(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)
    order = _place_order(api_client, db_session)

    response = api_client.get(
        "/api/v1/admin/orders", params={"order_number": order["order_number"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["order_number"] == order["order_number"]
    assert body["items"][0]["payment_status"] == "unpaid"
    assert body["items"][0]["items_summary"] == ["1× " + order["items"][0]["name_en"]]


def test_list_orders_filters_by_status(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)
    paid = _place_order(api_client, db_session, pay=True)
    _place_order(api_client, db_session, pay=False)

    response = api_client.get("/api/v1/admin/orders", params={"status": "paid"})

    assert response.status_code == 200
    order_numbers = {item["order_number"] for item in response.json()["items"]}
    assert paid["order_number"] in order_numbers


def test_get_order_detail_includes_operational_sections(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    response = api_client.get(f"/api/v1/admin/orders/{order['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["payment_status"] == "paid"
    assert len(body["payments"]) == 1
    assert body["odoo"]["sync_status"] == "not_synced"
    assert len(body["status_history"]) == 2  # pending_payment, paid


def test_valid_status_transition_succeeds_and_writes_history_and_audit(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    response = api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processing"
    assert [e["status"] for e in body["status_history"]] == [
        "pending_payment",
        "paid",
        "processing",
    ]
    assert any(a["action"] == "admin.order_status_updated" for a in body["audit_events"])


def test_invalid_status_transition_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=False)  # still pending_payment

    response = api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 409


def test_cancellation_requires_a_reason(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=False)

    response = api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "cancelled"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_cancellation_of_paid_order_marks_refund_pending(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    response = api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "cancelled", "note": "Customer requested cancellation"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["refund_status"] == "pending"
    assert body["cancellation_reason"] == "Customer requested cancellation"


def test_payment_status_never_changed_by_status_endpoint(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers={"X-CSRF-Token": csrf},
    )

    payments = api_client.get(f"/api/v1/admin/orders/{order['id']}/payments").json()
    assert len(payments) == 1
    assert payments[0]["status"] == "succeeded"


def test_retry_odoo_sync_requeues_a_failed_event(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    # Simulate a prior failed sync attempt (the stub pusher never actually fails).
    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"], OrderOutboxEvent.event_type == "order.paid"
        )
    ).scalar_one()
    event.status = "failed"
    event.attempts = 1
    db_session.flush()

    response = api_client.post(
        f"/api/v1/admin/orders/{order['id']}/retry-odoo-sync", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 200, response.text
    assert response.json()["queued"] is True
    db_session.refresh(event)
    assert event.status == "pending"


def test_retry_odoo_sync_without_a_failed_event_returns_409(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)  # event is "pending", not "failed"

    response = api_client.post(
        f"/api/v1/admin/orders/{order['id']}/retry-odoo-sync", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 409


def test_support_admin_cannot_update_order_status(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    response = api_client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        json={"status": "processing"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 403


def test_support_admin_can_retry_notification(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    csrf = login_as(api_client, admin)
    order = _place_order(api_client, db_session, pay=True)

    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"], OrderOutboxEvent.event_type == "order.notify"
        )
    ).scalar_one()
    event.status = "failed"
    db_session.flush()

    response = api_client.post(
        f"/api/v1/admin/orders/{order['id']}/retry-notification", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 200, response.text
