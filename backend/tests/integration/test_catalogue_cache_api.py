"""Endpoint-level cache-aside behaviour for GET /api/v1/catalogue/* (task brief §17
"Endpoint caching" list). Uses the real test Redis (REDIS_URL=.../15, flushed by the
`flush_cache` fixture) plus the savepoint-isolated `db_session` fixture for Postgres.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cache import RedisCache, get_cache_client
from app.cache.keys import homepage_key
from app.core.config import Settings, get_settings
from app.dependencies import get_app_settings, get_db
from app.main import app
from app.services.catalogue.catalogue_query_service import CatalogueQueryService
from tests.integration.catalogue_factories import (
    make_category,
    make_moment,
    make_product_with_default_variant,
    make_recipient,
)

pytestmark = pytest.mark.usefixtures("flush_cache")


@contextmanager
def _spy_on(cls: type, method_name: str) -> Generator[dict[str, int], None, None]:
    """`unittest.mock.patch.object(cls, name, wraps=cls.method)` loses `self` binding
    once the class attribute is a MagicMock (Mock objects aren't descriptors, so
    `instance.method` no longer goes through Python's normal bound-method machinery) —
    a plain function assigned to the class attribute doesn't have that problem, since
    ordinary functions are still descriptors."""
    original = getattr(cls, method_name)
    calls = {"count": 0}

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        return original(self, *args, **kwargs)

    with patch.object(cls, method_name, wrapper):
        yield calls


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _override_settings(**changes: object) -> Settings:
    return get_settings().model_copy(update=changes)


@pytest.fixture(autouse=True)
def _clear_settings_override() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.pop(get_app_settings, None)
    app.dependency_overrides.pop(get_cache_client, None)


def test_homepage_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, slug="cupcakes")
    make_product_with_default_variant(db_session, category=category)

    with _spy_on(CatalogueQueryService, "get_homepage") as calls:
        first = api_client.get("/api/v1/catalogue/homepage")
        second = api_client.get("/api/v1/catalogue/homepage")

    assert first.status_code == 200
    assert first.headers["X-Cache"] == "MISS"
    assert second.status_code == 200
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()
    # The second request never reached the query service — proof it was served
    # entirely from Redis, not by re-querying PostgreSQL.
    assert calls["count"] == 1


def test_categories_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    make_category(db_session, name_en="Visible")

    first = api_client.get("/api/v1/catalogue/categories")
    second = api_client.get("/api/v1/catalogue/categories")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()


def test_moments_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    make_moment(db_session, name_en="Birthday")

    first = api_client.get("/api/v1/catalogue/moments")
    second = api_client.get("/api/v1/catalogue/moments")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"


def test_recipients_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    make_recipient(db_session, name_en="For Her")

    first = api_client.get("/api/v1/catalogue/recipients")
    second = api_client.get("/api/v1/catalogue/recipients")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"


def test_product_detail_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    product = make_product_with_default_variant(db_session, category=category, slug="test-cake")

    with _spy_on(CatalogueQueryService, "get_product_detail") as calls:
        first = api_client.get(f"/api/v1/catalogue/products/{product.slug}")
        second = api_client.get(f"/api/v1/catalogue/products/{product.slug}")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert calls["count"] == 1


def test_product_detail_not_found_is_correct_and_never_cached(
    api_client: TestClient, db_session: Session
) -> None:
    with _spy_on(CatalogueQueryService, "get_product_detail") as calls:
        first = api_client.get("/api/v1/catalogue/products/does-not-exist")
        second = api_client.get("/api/v1/catalogue/products/does-not-exist")

    assert first.status_code == 404
    assert second.status_code == 404
    # A not-found result is never cached — the service is queried both times.
    assert calls["count"] == 2


def test_expired_entry_rebuilds(api_client: TestClient, db_session: Session) -> None:
    make_category(db_session, name_en="Expiring")
    app.dependency_overrides[get_app_settings] = lambda: _override_settings(
        cache_categories_ttl_seconds=1
    )

    first = api_client.get("/api/v1/catalogue/categories")
    time.sleep(1.2)
    second = api_client.get("/api/v1/catalogue/categories")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "MISS"


def test_cache_enabled_false_bypasses_redis(api_client: TestClient, db_session: Session) -> None:
    make_category(db_session, name_en="Unaffected")
    app.dependency_overrides[get_app_settings] = lambda: _override_settings(cache_enabled=False)

    first = api_client.get("/api/v1/catalogue/categories")
    second = api_client.get("/api/v1/catalogue/categories")

    assert first.headers["X-Cache"] == "BYPASS"
    assert second.headers["X-Cache"] == "BYPASS"


def test_redis_unavailable_falls_back_to_postgres(
    api_client: TestClient, db_session: Session
) -> None:
    make_category(db_session, name_en="StillWorks")
    broken_settings = _override_settings(
        redis_url="redis://localhost:1/15", cache_redis_operation_timeout_seconds=0.2
    )
    app.dependency_overrides[get_cache_client] = lambda: RedisCache(broken_settings)

    response = api_client.get("/api/v1/catalogue/categories")

    assert response.status_code == 200
    assert "StillWorks" in {c["name_en"] for c in response.json()}
    assert response.headers["X-Cache"] == "ERROR-FALLBACK"


def test_unsuccessful_response_is_not_cached(api_client: TestClient, db_session: Session) -> None:
    make_category(db_session, name_en="AfterFailure")

    # raise_server_exceptions=False: BaseHTTPMiddleware (used for correlation-id/
    # request-logging) re-raises an already-handled exception through TestClient's
    # ASGI transport by default — the real ASGI server always sees the clean 500
    # JSONResponse core/errors.py's `unhandled_exception_handler` builds; this flag
    # just makes the test see that same response instead of the transport's re-raise.
    non_raising_client = TestClient(app, raise_server_exceptions=False)
    with patch.object(CatalogueQueryService, "get_homepage", side_effect=RuntimeError("boom")):
        failed = non_raising_client.get("/api/v1/catalogue/homepage")
    assert failed.status_code == 500

    recovered = api_client.get("/api/v1/catalogue/homepage")
    assert recovered.status_code == 200
    # If the failed call had been cached, this would be a HIT on a nonexistent value
    # rather than a fresh, successful MISS.
    assert recovered.headers["X-Cache"] == "MISS"


def test_no_private_customer_data_shape_in_cached_homepage(
    api_client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session)
    make_product_with_default_variant(db_session, category=category)

    api_client.get("/api/v1/catalogue/homepage")

    cache = get_cache_client()
    cached_raw = cache.get_json(homepage_key(get_settings().cache_key_prefix))
    assert cached_raw is not None
    serialized = str(cached_raw).lower()
    for forbidden in ("email", "phone", "customer_id", "payment", "card_number"):
        assert forbidden not in serialized
