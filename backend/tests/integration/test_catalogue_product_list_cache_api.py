"""Cache behaviour for the optional GET /api/v1/catalogue/products list endpoint
(task brief §15 "Product-list cache control")."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.dependencies import get_app_settings, get_db
from app.main import app
from tests.integration.catalogue_factories import make_category, make_product_with_default_variant

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


@pytest.fixture(autouse=True)
def _clear_settings_override() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.pop(get_app_settings, None)


def test_product_list_miss_then_hit(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, slug="cakes")
    make_product_with_default_variant(db_session, category=category)

    first = api_client.get("/api/v1/catalogue/products", params={"category": "cakes"})
    second = api_client.get("/api/v1/catalogue/products", params={"category": "cakes"})

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()


def test_product_list_parameter_order_does_not_affect_cache_hit(
    api_client: TestClient, db_session: Session
) -> None:
    # Any category slug works here — this test only cares about parameter-order
    # normalization, not the homepage hero-section business rule, so it deliberately
    # avoids "cupcakes" (a hardcoded slug other test files also use).
    category = make_category(db_session, slug="param-order-category")
    make_product_with_default_variant(db_session, category=category)

    first = api_client.get(
        "/api/v1/catalogue/products",
        params={"category": "param-order-category", "limit": 10, "offset": 0},
    )
    second = api_client.get(
        "/api/v1/catalogue/products",
        params={"offset": 0, "limit": 10, "category": "param-order-category"},
    )

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"


def test_product_list_bypasses_cache_for_high_offset(
    api_client: TestClient, db_session: Session
) -> None:
    make_category(db_session)

    response = api_client.get("/api/v1/catalogue/products", params={"offset": 500})

    assert response.headers["X-Cache"] == "BYPASS"


def test_product_list_bypasses_cache_for_long_search(
    api_client: TestClient, db_session: Session
) -> None:
    make_category(db_session)

    response = api_client.get("/api/v1/catalogue/products", params={"search": "x" * 41})

    assert response.headers["X-Cache"] == "BYPASS"


def test_product_list_key_space_guard_stops_caching_new_variants_past_the_cap(
    api_client: TestClient, db_session: Session
) -> None:
    make_category(db_session, slug="one")
    make_category(db_session, slug="two")
    app.dependency_overrides[get_app_settings] = lambda: get_settings().model_copy(
        update={"cache_max_product_list_keys": 1}
    )

    first = api_client.get("/api/v1/catalogue/products", params={"category": "one"})
    second = api_client.get("/api/v1/catalogue/products", params={"category": "two"})
    # Re-requesting the already-tracked first variant is still allowed.
    first_again = api_client.get("/api/v1/catalogue/products", params={"category": "one"})

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "BYPASS"
    assert first_again.headers["X-Cache"] == "HIT"
