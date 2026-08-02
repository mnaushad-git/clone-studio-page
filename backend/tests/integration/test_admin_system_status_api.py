"""Endpoint-level tests for /api/v1/admin/system/status (task brief §9)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from tests.integration.admin_factories import login_as, make_admin_user


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_system_status_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/admin/system/status").status_code == 401


def test_system_status_shape(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "up"
    assert body["payment_provider_mode"] == "stub"
    assert body["notification_provider_mode"] == "stub"
    assert body["odoo_order_push_mode"] == "stub"
    assert body["stub_providers_active"] is True
    assert body["cache_enabled"] is True
    assert body["cache_key_version"] == "v1"
    assert isinstance(body["cache_hits"], int)
    assert isinstance(body["cache_misses"], int)
    assert isinstance(body["cache_errors"], int)
    # No credentials or connection strings ever leak into this response.
    for value in body.values():
        assert "postgresql://" not in str(value)
        assert "redis://" not in str(value)
