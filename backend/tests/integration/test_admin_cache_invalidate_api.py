"""POST /api/v1/admin/system/cache/invalidate (task brief §19 — optional admin
action; the invalidation service it calls is mandatory and already covered by
test_cache_invalidation.py)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cache import RedisCache
from app.cache.keys import homepage_key
from app.core.config import get_settings
from app.dependencies import get_db
from app.main import app
from tests.integration.admin_factories import login_as, make_admin_user

pytestmark = pytest.mark.usefixtures("flush_cache")


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_requires_authentication(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/admin/system/cache/invalidate", json={"operation": "homepage"}
    )
    assert response.status_code == 401


def test_non_super_admin_is_forbidden(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPPORT_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/system/cache/invalidate",
        json={"operation": "homepage"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 403


def test_product_operation_requires_slug(api_client: TestClient, db_session: Session) -> None:
    admin = make_admin_user(db_session, role="SUPER_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/system/cache/invalidate",
        json={"operation": "product"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422


def test_homepage_invalidation_returns_deleted_key_count(
    api_client: TestClient, db_session: Session
) -> None:
    cache = RedisCache(get_settings())
    prefix = get_settings().cache_key_prefix
    cache.set_json(homepage_key(prefix), {"v": 1}, ttl_seconds=60)
    admin = make_admin_user(db_session, role="SUPER_ADMIN")
    csrf = login_as(api_client, admin)

    response = api_client.post(
        "/api/v1/admin/system/cache/invalidate",
        json={"operation": "homepage"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "homepage"
    assert body["deleted_keys"] == 1
    assert cache.get_json(homepage_key(prefix)) is None
