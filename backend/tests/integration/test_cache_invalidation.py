"""CacheInvalidationService + its wiring into the Odoo catalogue sync and admin
merchandising update commit points (task brief §9, §10, §11, §17 "Invalidation" list).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cache import RedisCache
from app.cache.invalidation import CacheInvalidationService
from app.cache.keys import (
    ProductListFilters,
    categories_key,
    homepage_key,
    moments_key,
    product_detail_key,
    product_list_key,
    recipients_key,
)
from app.core.config import get_settings
from app.dependencies import get_db
from app.main import app
from app.services.catalogue.odoo_catalogue_sync_service import OdooCatalogueSyncService
from tests.integration.admin_factories import login_as, make_admin_user
from tests.integration.catalogue_factories import (
    make_category,
    make_merchandising,
    make_product_with_default_variant,
)

pytestmark = pytest.mark.usefixtures("flush_cache")


@pytest.fixture
def cache() -> RedisCache:
    return RedisCache(get_settings())


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed_all_keys(cache: RedisCache, slug: str) -> None:
    prefix = get_settings().cache_key_prefix
    cache.set_json(homepage_key(prefix), {"v": 1}, ttl_seconds=60)
    cache.set_json(categories_key(prefix), {"v": 1}, ttl_seconds=60)
    cache.set_json(moments_key(prefix), {"v": 1}, ttl_seconds=60)
    cache.set_json(recipients_key(prefix), {"v": 1}, ttl_seconds=60)
    cache.set_json(product_detail_key(prefix, slug), {"v": 1}, ttl_seconds=60)
    cache.set_json(product_list_key(prefix, ProductListFilters()), {"v": 1}, ttl_seconds=60)


def test_invalidate_homepage_only_removes_homepage_key(cache: RedisCache) -> None:
    _seed_all_keys(cache, "cake")
    service = CacheInvalidationService(cache, get_settings())

    deleted = service.invalidate_homepage()

    assert deleted == 1
    prefix = get_settings().cache_key_prefix
    assert cache.get_json(homepage_key(prefix)) is None
    assert cache.get_json(categories_key(prefix)) is not None


def test_invalidate_product_removes_only_that_slugs_detail_key(cache: RedisCache) -> None:
    prefix = get_settings().cache_key_prefix
    cache.set_json(product_detail_key(prefix, "cake-a"), {"v": 1}, ttl_seconds=60)
    cache.set_json(product_detail_key(prefix, "cake-b"), {"v": 1}, ttl_seconds=60)
    service = CacheInvalidationService(cache, get_settings())

    deleted = service.invalidate_product("cake-a")

    assert deleted == 1
    assert cache.get_json(product_detail_key(prefix, "cake-a")) is None
    assert cache.get_json(product_detail_key(prefix, "cake-b")) is not None


def test_invalidate_product_lists_clears_the_whole_namespace(cache: RedisCache) -> None:
    prefix = get_settings().cache_key_prefix
    cache.set_json(
        product_list_key(prefix, ProductListFilters(category="cakes")), {"v": 1}, ttl_seconds=60
    )
    cache.set_json(
        product_list_key(prefix, ProductListFilters(category="cupcakes")), {"v": 1}, ttl_seconds=60
    )
    service = CacheInvalidationService(cache, get_settings())

    assert service.invalidate_product_lists() == 2


def test_invalidate_catalogue_all_clears_every_resource(cache: RedisCache) -> None:
    _seed_all_keys(cache, "cake")
    service = CacheInvalidationService(cache, get_settings())

    deleted = service.invalidate_catalogue_all()

    assert deleted == 6
    prefix = get_settings().cache_key_prefix
    assert cache.get_json(homepage_key(prefix)) is None
    assert cache.get_json(categories_key(prefix)) is None
    assert cache.get_json(moments_key(prefix)) is None
    assert cache.get_json(recipients_key(prefix)) is None
    assert cache.get_json(product_detail_key(prefix, "cake")) is None
    assert cache.get_json(product_list_key(prefix, ProductListFilters())) is None


def test_invalidate_after_product_sync_skips_on_failed_status(cache: RedisCache) -> None:
    _seed_all_keys(cache, "cake")
    service = CacheInvalidationService(cache, get_settings())

    deleted = service.invalidate_after_product_sync("FAILED")

    assert deleted == 0
    prefix = get_settings().cache_key_prefix
    assert cache.get_json(homepage_key(prefix)) is not None


def test_invalidate_after_product_sync_invalidates_on_succeeded_status(cache: RedisCache) -> None:
    _seed_all_keys(cache, "cake")
    service = CacheInvalidationService(cache, get_settings())

    deleted = service.invalidate_after_product_sync("SUCCEEDED")

    assert deleted == 6
    prefix = get_settings().cache_key_prefix
    assert cache.get_json(homepage_key(prefix)) is None


def test_invalidate_after_product_sync_invalidates_on_partially_completed_status(
    cache: RedisCache,
) -> None:
    _seed_all_keys(cache, "cake")
    service = CacheInvalidationService(cache, get_settings())

    assert service.invalidate_after_product_sync("PARTIALLY_COMPLETED") == 6


def test_invalidate_after_merchandising_update_targets_product_homepage_and_lists(
    cache: RedisCache,
) -> None:
    prefix = get_settings().cache_key_prefix
    cache.set_json(product_detail_key(prefix, "cake"), {"v": 1}, ttl_seconds=60)
    cache.set_json(homepage_key(prefix), {"v": 1}, ttl_seconds=60)
    cache.set_json(categories_key(prefix), {"v": 1}, ttl_seconds=60)  # must NOT be touched
    cache.set_json(
        product_list_key(prefix, ProductListFilters(category="cakes")), {"v": 1}, ttl_seconds=60
    )
    service = CacheInvalidationService(cache, get_settings())

    service.invalidate_after_merchandising_update("cake")

    assert cache.get_json(product_detail_key(prefix, "cake")) is None
    assert cache.get_json(homepage_key(prefix)) is None
    assert cache.get_json(product_list_key(prefix, ProductListFilters(category="cakes"))) is None
    assert cache.get_json(categories_key(prefix)) is not None


def test_odoo_sync_with_odoo_unconfigured_marks_run_failed_and_does_not_invalidate(
    db_session: Session, cache: RedisCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The suite must never depend on external Odoo (CLAUDE.md) — force Odoo
    unconfigured for this test regardless of what a developer's local .env happens to
    have, so this exercises the real "Odoo unreachable" branch of sync_all() on every
    machine, not just ones without Odoo configured."""
    unconfigured = get_settings().model_copy(
        update={"odoo_base_url": "", "odoo_database": "", "odoo_username": ""}
    )
    monkeypatch.setattr(
        "app.services.catalogue.odoo_catalogue_sync_service.get_settings", lambda: unconfigured
    )
    prefix = get_settings().cache_key_prefix
    cache.set_json(homepage_key(prefix), {"v": 1}, ttl_seconds=60)

    run = OdooCatalogueSyncService(db_session).sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id=str(uuid.uuid4())
    )

    assert run.status == "FAILED"
    assert cache.get_json(homepage_key(prefix)) is not None


def test_admin_merchandising_update_invalidates_cache_after_commit(
    api_client: TestClient, db_session: Session, cache: RedisCache
) -> None:
    category = make_category(db_session)
    product = make_product_with_default_variant(db_session, category=category)

    make_merchandising(db_session, product)
    admin = make_admin_user(db_session)
    csrf = login_as(api_client, admin)

    prefix = get_settings().cache_key_prefix
    cache.set_json(product_detail_key(prefix, product.slug), {"stale": True}, ttl_seconds=60)
    cache.set_json(homepage_key(prefix), {"stale": True}, ttl_seconds=60)

    response = api_client.patch(
        f"/api/v1/admin/products/{product.id}/merchandising",
        json={"featured": True},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert cache.get_json(product_detail_key(prefix, product.slug)) is None
    assert cache.get_json(homepage_key(prefix)) is None


def test_failed_merchandising_update_does_not_invalidate_cache(
    api_client: TestClient, db_session: Session, cache: RedisCache
) -> None:
    category = make_category(db_session)
    product = make_product_with_default_variant(db_session, category=category)

    make_merchandising(db_session, product)
    admin = make_admin_user(db_session)
    csrf = login_as(api_client, admin)

    prefix = get_settings().cache_key_prefix
    cache.set_json(product_detail_key(prefix, product.slug), {"stale": True}, ttl_seconds=60)

    # `sku` is Odoo-owned, not an editable merchandising field — rejected before any
    # commit happens.
    response = api_client.patch(
        f"/api/v1/admin/products/{product.id}/merchandising",
        json={"sku": "NEW-SKU"},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code >= 400
    assert cache.get_json(product_detail_key(prefix, product.slug)) == {"stale": True}
