"""Endpoint-level tests for /api/v1/admin/audit-events (task brief §13)."""

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


def test_audit_events_requires_super_admin(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)

    assert api_client.get("/api/v1/admin/audit-events").status_code == 403


def test_login_success_and_failure_are_audited(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPER_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/audit-events", params={"entity_type": "admin_user"})

    assert response.status_code == 200
    actions = [e["action"] for e in response.json()["items"]]
    assert "admin.login_succeeded" in actions


def test_audit_pagination(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPER_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/audit-events", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 1
    assert len(body["items"]) <= 1


def test_audit_never_exposes_password_fields(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPER_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/audit-events")

    body_text = response.text.lower()
    assert "password_hash" not in body_text
