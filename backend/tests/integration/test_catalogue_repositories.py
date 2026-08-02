from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.catalogue.category_repository import CategoryRepository
from app.repositories.catalogue.product_repository import ProductRepository
from tests.integration.catalogue_factories import (
    make_category,
    make_product,
    make_product_with_default_variant,
)


def test_get_by_id_returns_none_for_missing_row(db_session: Session) -> None:
    import uuid

    repo = ProductRepository(db_session)
    assert repo.get_by_id(uuid.uuid4()) is None


def test_product_repository_get_by_sku(db_session: Session) -> None:
    product = make_product(db_session, sku="TB-REPO-001")
    repo = ProductRepository(db_session)

    found = repo.get_by_sku("TB-REPO-001")

    assert found is not None
    assert found.id == product.id
    assert repo.get_by_sku("TB-DOES-NOT-EXIST") is None


def test_category_repository_get_by_external_key(db_session: Session) -> None:
    category = make_category(db_session, external_key="test.category.repo-lookup")
    repo = CategoryRepository(db_session)

    found = repo.get_by_external_key("test.category.repo-lookup")

    assert found is not None
    assert found.id == category.id
    assert repo.get_by_external_key("test.category.does-not-exist") is None


def test_category_repository_list_active_excludes_inactive(db_session: Session) -> None:
    repo = CategoryRepository(db_session)
    active = make_category(db_session, active=True, display_order=1)
    make_category(db_session, active=False, display_order=2)

    results = repo.list_active()

    ids = {c.id for c in results}
    assert active.id in ids
    assert all(c.active for c in results)


def test_upsert_by_external_key_created_then_updated_then_noop(db_session: Session) -> None:
    repo = CategoryRepository(db_session)

    obj, created, changed = repo.upsert_by_external_key(
        "test.category.upsert",
        {
            "code": "UPSERT1",
            "slug": "upsert-category",
            "name_en": "Original Name",
            "active": True,
            "display_order": 0,
        },
    )
    assert created is True
    assert changed is False

    obj2, created2, changed2 = repo.upsert_by_external_key(
        "test.category.upsert",
        {
            "code": "UPSERT1",
            "slug": "upsert-category",
            "name_en": "Changed Name",
            "active": True,
            "display_order": 0,
        },
    )
    assert created2 is False
    assert changed2 is True
    assert obj2.id == obj.id
    assert obj2.name_en == "Changed Name"

    obj3, created3, changed3 = repo.upsert_by_external_key(
        "test.category.upsert",
        {
            "code": "UPSERT1",
            "slug": "upsert-category",
            "name_en": "Changed Name",
            "active": True,
            "display_order": 0,
        },
    )
    assert created3 is False
    assert changed3 is False
    assert obj3.id == obj.id


def test_category_repository_get_by_slug(db_session: Session) -> None:
    category = make_category(db_session, slug="repo-slug-lookup")
    repo = CategoryRepository(db_session)

    assert repo.get_by_slug("repo-slug-lookup") is not None
    assert repo.get_by_slug("repo-slug-lookup").id == category.id
    assert repo.get_by_slug("no-such-slug") is None


def test_product_repository_get_by_slug(db_session: Session) -> None:
    product = make_product(db_session, slug="repo-product-slug")
    repo = ProductRepository(db_session)

    found = repo.get_by_slug("repo-product-slug")

    assert found is not None
    assert found.id == product.id
    assert repo.get_by_slug("missing") is None


def test_product_repository_search_only_active_paginated(db_session: Session) -> None:
    category = make_category(db_session)
    active_products = [
        make_product_with_default_variant(db_session, category=category, name_en=f"P{i}")
        for i in range(3)
    ]
    make_product_with_default_variant(
        db_session, category=category, name_en="Inactive", active=False
    )
    repo = ProductRepository(db_session)

    items, total = repo.search(category_slug=category.slug, limit=2, offset=0)

    assert total == 3  # inactive product excluded from the count
    assert len(items) == 2
    assert {p.id for p in items}.issubset({p.id for p in active_products})
