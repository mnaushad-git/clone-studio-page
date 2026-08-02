"""Endpoint-level tests for /api/v1/admin/auth/* — same TestClient + savepoint-
isolated db_session pattern as test_orders_api.py.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from tests.integration.admin_factories import DEFAULT_PASSWORD, login_as, make_admin_user


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_login_success_sets_cookies_and_returns_profile(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)

    response = api_client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == admin.email
    assert body["role"] == "SUPER_ADMIN"
    assert "password" not in body and "password_hash" not in body
    assert "admin_access_token" in api_client.cookies
    assert "admin_refresh_token" in api_client.cookies
    assert "admin_csrf" in api_client.cookies


def test_login_invalid_password_returns_generic_error(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)

    response = api_client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_login_unknown_email_returns_same_generic_error(
    api_client: TestClient, db_session: Session
) -> None:
    response = api_client.post(
        "/api/v1/admin/auth/login",
        json={"email": "nobody@test.terrificbites.sa", "password": "whatever"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_login_disabled_user_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, is_active=False)

    response = api_client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 401


def test_login_locked_user_rejected(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, locked_until=datetime.now(UTC) + timedelta(minutes=10))

    response = api_client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 401


def test_repeated_failed_logins_lock_the_account(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)

    for _ in range(5):
        api_client.post(
            "/api/v1/admin/auth/login", json={"email": admin.email, "password": "wrong"}
        )

    db_session.refresh(admin)
    assert admin.locked_until is not None

    # Even the correct password is now rejected until the lock expires.
    response = api_client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 401


def test_me_requires_authentication(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/admin/auth/me")
    assert response.status_code == 401


def test_me_returns_current_admin_after_login(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session)
    login_as(api_client, admin)

    response = api_client.get("/api/v1/admin/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == admin.email


def test_logout_revokes_session(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session)
    csrf = login_as(api_client, admin)

    response = api_client.post("/api/v1/admin/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200

    me_response = api_client.get("/api/v1/admin/auth/me")
    assert me_response.status_code == 401


def test_mutating_request_without_csrf_header_is_rejected(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)
    login_as(api_client, admin)

    response = api_client.post("/api/v1/admin/auth/logout")

    assert response.status_code == 403


def test_refresh_rotates_tokens(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session)
    login_as(api_client, admin)
    old_refresh = api_client.cookies["admin_refresh_token"]

    response = api_client.post("/api/v1/admin/auth/refresh")

    assert response.status_code == 200
    # The refresh token (unlike the access JWT, which can collide byte-for-byte if
    # issued within the same second) is a fresh random value every time — the
    # strongest signal that rotation actually happened.
    assert api_client.cookies["admin_refresh_token"] != old_refresh
    # The old refresh token must no longer work.
    api_client.cookies.set("admin_refresh_token", old_refresh)
    replay_response = api_client.post("/api/v1/admin/auth/refresh")
    assert replay_response.status_code == 401


def test_change_password_requires_correct_current_password(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/auth/change-password",
        json={"current_password": "wrong", "new_password": "NewPassw0rd!"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 401


def test_change_password_success_invalidates_session(
    api_client: TestClient, db_session: Session
) -> None:
    admin = make_admin_user(db_session)
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "NewPassw0rd!"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    # The old session was revoked as part of the password change.
    assert api_client.get("/api/v1/admin/auth/me").status_code == 401


def test_role_permission_denied_for_wrong_role(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    login_as(api_client, admin)

    # SUPPORT_ADMIN has no promo-code access (CATALOGUE_ADMIN/SUPER_ADMIN only).
    response = api_client.get("/api/v1/admin/promo-codes")

    assert response.status_code == 403
