"""Endpoint-level tests for /api/v1/admin/promo-codes/*."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from tests.integration.admin_factories import login_as, make_admin_user, make_promo_code


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_create_promo_code(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/promo-codes",
        json={"code": "newcode10", "discount_type": "PERCENTAGE", "discount_value": 10},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == "NEWCODE10"  # normalized uppercase
    assert body["usage_count"] == 0


def test_duplicate_code_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)
    existing = make_promo_code(db_session, code="DUPTEST")

    response = api_client.post(
        "/api/v1/admin/promo-codes",
        json={"code": existing.code, "discount_type": "PERCENTAGE", "discount_value": 5},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 409


def test_percentage_over_100_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/promo-codes",
        json={"code": "TOOMUCH", "discount_type": "PERCENTAGE", "discount_value": 150},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_fixed_discount_must_be_positive(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/promo-codes",
        json={"code": "ZEROFIXED", "discount_type": "FIXED_AMOUNT", "discount_value": 0},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_valid_until_before_valid_from_rejected(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/promo-codes",
        json={
            "code": "BADDATES",
            "discount_type": "PERCENTAGE",
            "discount_value": 10,
            "valid_from": "2026-06-01T00:00:00Z",
            "valid_until": "2026-05-01T00:00:00Z",
        },
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_deactivate_promo_code(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)
    promo = make_promo_code(db_session)

    response = api_client.patch(
        f"/api/v1/admin/promo-codes/{promo.id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_unused_promo_code_succeeds(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)
    promo = make_promo_code(db_session, usage_count=0)

    response = api_client.delete(
        f"/api/v1/admin/promo-codes/{promo.id}", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 204


def test_delete_used_promo_code_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)
    promo = make_promo_code(db_session, usage_count=3)

    response = api_client.delete(
        f"/api/v1/admin/promo-codes/{promo.id}", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 409


def test_usage_limit_cannot_drop_below_current_usage(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)
    promo = make_promo_code(db_session, usage_count=5, usage_limit=10)

    response = api_client.patch(
        f"/api/v1/admin/promo-codes/{promo.id}",
        json={"usage_limit": 2},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_checkout_uses_database_promo_code(api_client: TestClient, db_session: Session) -> None:
    from decimal import Decimal

    from tests.integration.catalogue_factories import make_product_with_default_variant

    promo = make_promo_code(
        db_session, code="DBPROMO", discount_type="PERCENTAGE", discount_value=20
    )
    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))

    response = api_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": promo.code.lower(),
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
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["promo_code"] == "DBPROMO"
    assert body["discount_amount"] == "20.00"

    db_session.refresh(promo)
    assert promo.usage_count == 1


def test_unknown_promo_code_rejected_at_checkout(
    api_client: TestClient, db_session: Session
) -> None:
    from decimal import Decimal

    from tests.integration.catalogue_factories import make_product_with_default_variant

    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))

    response = api_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": "DOES-NOT-EXIST",
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
        },
    )

    assert response.status_code == 422
