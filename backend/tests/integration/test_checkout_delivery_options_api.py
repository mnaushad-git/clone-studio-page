"""Endpoint-level tests for the public GET /api/v1/checkout/delivery-options
(task brief §12) — no authentication required, the Storefront calls this directly."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_delivery_options_is_public(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/checkout/delivery-options")

    assert response.status_code == 200
    body = response.json()
    assert "flat_delivery_fee" in body
    assert isinstance(body["slots"], list)
    assert all(slot["active"] for slot in body["slots"])


def test_delivery_options_reflects_admin_edits(api_client: TestClient, db_session: Session) -> None:
    from tests.integration.admin_factories import login_as, make_admin_user

    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    api_client.patch(
        "/api/v1/admin/delivery-settings",
        json={"flat_delivery_fee": 99.99},
        headers={"X-CSRF-Token": csrf},
    )

    response = api_client.get("/api/v1/checkout/delivery-options")

    assert response.json()["flat_delivery_fee"] == "99.99"
