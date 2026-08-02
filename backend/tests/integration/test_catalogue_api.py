"""Endpoint-level tests for /api/v1/catalogue/* — exercises the real FastAPI app via
TestClient, with the `get_db` dependency overridden to reuse the test's savepoint-
isolated `db_session` (never a second, real connection that wouldn't see fixture data
inserted but not committed).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from tests.integration.catalogue_factories import (
    make_category,
    make_merchandising,
    make_moment,
    make_product_with_default_variant,
    make_recipient,
)


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_categories_returns_only_active(api_client: TestClient, db_session: Session) -> None:
    make_category(db_session, active=True, name_en="Visible")
    make_category(db_session, active=False, name_en="Hidden")

    response = api_client.get("/api/v1/catalogue/categories")

    assert response.status_code == 200
    names = {c["name_en"] for c in response.json()}
    assert "Visible" in names
    assert "Hidden" not in names


def test_get_moments_and_recipients(api_client: TestClient, db_session: Session) -> None:
    make_moment(db_session, name_en="Birthday")
    make_recipient(db_session, name_en="For Her")

    moments = api_client.get("/api/v1/catalogue/moments")
    recipients = api_client.get("/api/v1/catalogue/recipients")

    assert moments.status_code == 200
    assert "Birthday" in {m["name_en"] for m in moments.json()}
    assert recipients.status_code == 200
    assert "For Her" in {r["name_en"] for r in recipients.json()}


def test_list_products_default_pagination_shape(
    api_client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session)
    make_product_with_default_variant(db_session, category=category, name_en="Alpha")
    make_product_with_default_variant(db_session, category=category, name_en="Bravo")

    response = api_client.get("/api/v1/catalogue/products")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [p["name_en"] for p in body["items"]] == ["Alpha", "Bravo"]


def test_list_products_category_filter(api_client: TestClient, db_session: Session) -> None:
    cat_a = make_category(db_session, slug="filter-a")
    cat_b = make_category(db_session, slug="filter-b")
    make_product_with_default_variant(db_session, category=cat_a, name_en="In A")
    make_product_with_default_variant(db_session, category=cat_b, name_en="In B")

    response = api_client.get("/api/v1/catalogue/products", params={"category": "filter-a"})

    assert response.status_code == 200
    body = response.json()
    assert [p["name_en"] for p in body["items"]] == ["In A"]


def test_list_products_featured_filter(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    featured = make_product_with_default_variant(db_session, category=category, name_en="Star")
    make_merchandising(db_session, featured, featured=True)
    plain = make_product_with_default_variant(db_session, category=category, name_en="Plain")
    make_merchandising(db_session, plain, featured=False)

    response = api_client.get("/api/v1/catalogue/products", params={"featured": "true"})

    assert response.status_code == 200
    assert [p["name_en"] for p in response.json()["items"]] == ["Star"]


def test_list_products_pagination_limit_offset(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    for name in ["Alpha", "Bravo", "Charlie"]:
        make_product_with_default_variant(db_session, category=category, name_en=name)

    response = api_client.get(
        "/api/v1/catalogue/products", params={"limit": 2, "offset": 1, "category": category.slug}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [p["name_en"] for p in body["items"]] == ["Bravo", "Charlie"]


def test_get_product_detail_by_slug(api_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    make_product_with_default_variant(db_session, category=category, slug="api-detail-product")

    response = api_client.get("/api/v1/catalogue/products/api-detail-product")

    assert response.status_code == 200
    assert response.json()["slug"] == "api-detail-product"


def test_get_product_detail_404_for_missing_slug(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/catalogue/products/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "correlation_id" in body["error"]


def test_get_homepage_returns_all_sections(api_client: TestClient, db_session: Session) -> None:
    cupcakes = make_category(db_session, slug="cupcakes")
    p = make_product_with_default_variant(db_session, category=cupcakes, name_en="Cup 1")
    make_merchandising(db_session, p, display_order=1)

    response = api_client.get("/api/v1/catalogue/homepage")

    assert response.status_code == 200
    body = response.json()
    for key in ("hero", "gifts", "divine", "chocolates", "extras", "new"):
        assert key in body
    assert any(item["name_en"] == "Cup 1" for item in body["hero"])
