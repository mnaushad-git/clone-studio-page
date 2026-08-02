"""Endpoint-level tests for /api/v1/admin/catalogue-sync/*."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
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


def _make_run(db_session: Session, **overrides: object) -> OdooCatalogueSyncRun:
    defaults: dict[str, object] = {
        "trigger": "SCHEDULED",
        "status": "SUCCEEDED",
        "full_resync": False,
        "started_at": datetime.now(UTC),
        "completed_at": datetime.now(UTC),
        "correlation_id": "corr-test",
        "initiated_by": "celery-beat",
    }
    defaults.update(overrides)
    run = OdooCatalogueSyncRun(**defaults)
    db_session.add(run)
    db_session.flush()
    db_session.commit()
    return run


def test_list_sync_runs_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/admin/catalogue-sync/runs").status_code == 401


def test_list_sync_runs_returns_recent_runs(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    login_as(api_client, admin)
    _make_run(db_session)

    response = api_client.get("/api/v1/admin/catalogue-sync/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["status"] == "SUCCEEDED"


def test_get_sync_run_detail(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    login_as(api_client, admin)
    run = _make_run(db_session)

    response = api_client.get(f"/api/v1/admin/catalogue-sync/runs/{run.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(run.id)
    assert response.json()["items_detail"] == []


def test_support_admin_cannot_view_sync_runs(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/catalogue-sync/runs")

    assert response.status_code == 403


def test_trigger_sync_requires_csrf(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    login_as(api_client, admin)

    response = api_client.post("/api/v1/admin/catalogue-sync/trigger", json={"full_resync": False})

    assert response.status_code == 403


def test_trigger_sync_dispatches_task_and_creates_run(
    api_client: TestClient, db_session: Session
) -> None:
    """Celery runs in eager mode for the test suite (tests/conftest.py), so a
    successful .delay() call actually executes sync_catalogue_from_odoo synchronously
    — this asserts the full request-to-run pipeline, not just a mocked dispatch call.
    Odoo isn't configured in the test environment, so the eagerly-run task connects,
    fails fast, and records a FAILED run — which is still proof the whole wiring works
    end to end (route -> service -> Celery task -> OdooCatalogueSyncService -> DB row).
    """
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/catalogue-sync/trigger",
        json={"full_resync": False},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["queued"] is True

    runs = api_client.get("/api/v1/admin/catalogue-sync/runs").json()["items"]
    assert any(r["trigger"] == "MANUAL" and r["initiated_by"] == admin.email for r in runs)
