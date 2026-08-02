"""Test-only factories/helpers for Admin Portal endpoint tests — mirrors
catalogue_factories.py's style."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.admin.admin_user import AdminUser
from app.models.admin.promo_code import PromoCode

DEFAULT_PASSWORD = "TestPassw0rd!"


def make_admin_user(session: Session, **overrides: Any) -> AdminUser:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "email": f"admin-{suffix}@test.terrificbites.sa",
        "password_hash": hash_password(DEFAULT_PASSWORD),
        "full_name": f"Test Admin {suffix}",
        "role": "SUPER_ADMIN",
        "is_active": True,
    }
    defaults.update(overrides)
    admin = AdminUser(**defaults)
    session.add(admin)
    session.flush()
    return admin


def login_as(client: TestClient, admin: AdminUser, password: str = DEFAULT_PASSWORD) -> str:
    """Logs the given client in (cookies persist on it) and returns the CSRF token
    to pass as X-CSRF-Token on subsequent mutating requests."""
    response = client.post(
        "/api/v1/admin/auth/login", json={"email": admin.email, "password": password}
    )
    assert response.status_code == 200, response.text
    return client.cookies["admin_csrf"]


def make_promo_code(session: Session, **overrides: Any) -> PromoCode:
    suffix = uuid.uuid4().hex[:8].upper()
    defaults: dict[str, Any] = {
        "code": f"TEST{suffix}",
        "discount_type": "PERCENTAGE",
        "discount_value": 10,
        "minimum_order_amount": 0,
        "usage_count": 0,
        "is_active": True,
    }
    defaults.update(overrides)
    promo = PromoCode(**defaults)
    session.add(promo)
    session.flush()
    return promo
