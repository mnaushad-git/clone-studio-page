"""Cache invalidation service (task brief §9, §10, §11).

Single call site for every catalogue cache invalidation — nothing outside this module
ever calls RedisCache.delete*/delete_by_prefix directly for catalogue keys (task brief
§11: "Do not scatter wildcard Redis deletes throughout unrelated services").

Ordering contract callers must respect: only call these methods AFTER the PostgreSQL
transaction that changed the underlying data has committed. Never before — a cache
entry populated (or left stale) from an uncommitted transaction could serve data that
a rollback later makes wrong. See:
  - app/services/catalogue/odoo_catalogue_sync_service.py (sync_all, end of run)
  - app/api/v1/endpoints/admin/products.py (update_merchandising, after session.commit())
"""

from __future__ import annotations

import logging

from app.cache import keys
from app.cache.interface import CacheClient
from app.core.config import Settings

logger = logging.getLogger("app.cache.invalidation")

# Every locale bucket a cached response is currently stored under (see
# app/cache/keys.py module docstring — the API has no per-locale response variant
# today, so this is a single-element list, not a hardcoded constant baked into every
# key builder call).
_ALL_LOCALES = (keys.DEFAULT_LOCALE,)

# Sync-run statuses (app/models/integration/odoo_catalogue_sync_run.py) that mean at
# least the possibility of a committed catalogue change — FAILED means nothing was
# ever committed this run, so invalidating would just be needless cache churn (task
# brief §9: "If database sync fails, do not invalidate valid cache unnecessarily").
_SYNC_STATUSES_WORTH_INVALIDATING = frozenset({"SUCCEEDED", "PARTIALLY_COMPLETED"})


class CacheInvalidationService:
    def __init__(self, cache: CacheClient, settings: Settings) -> None:
        self._cache = cache
        self._prefix = settings.cache_key_prefix

    def invalidate_homepage(self) -> int:
        return self._cache.delete_many(
            [keys.homepage_key(self._prefix, loc) for loc in _ALL_LOCALES]
        )

    def invalidate_categories(self) -> int:
        return self._cache.delete_many(
            [keys.categories_key(self._prefix, loc) for loc in _ALL_LOCALES]
        )

    def invalidate_moments(self) -> int:
        return self._cache.delete_many(
            [keys.moments_key(self._prefix, loc) for loc in _ALL_LOCALES]
        )

    def invalidate_recipients(self) -> int:
        return self._cache.delete_many(
            [keys.recipients_key(self._prefix, loc) for loc in _ALL_LOCALES]
        )

    def invalidate_product(self, slug: str) -> int:
        """Bounded SCAN over just this product's key prefix (every locale variant),
        never a namespace-wide scan — cheap enough to call for a single product edit."""
        return self._cache.delete_by_prefix(keys.product_detail_prefix(self._prefix, slug))

    def invalidate_product_lists(self) -> int:
        return self._cache.delete_by_prefix(keys.product_list_namespace_prefix(self._prefix))

    def invalidate_catalogue_all(self) -> int:
        deleted = 0
        deleted += self.invalidate_homepage()
        deleted += self.invalidate_categories()
        deleted += self.invalidate_moments()
        deleted += self.invalidate_recipients()
        deleted += self.invalidate_product_lists()
        # Covers every cached product-detail slug in one bounded-batch SCAN — cheaper
        # and simpler than enumerating every slug that might have changed this run.
        deleted += self._cache.delete_by_prefix(keys.product_detail_namespace_prefix(self._prefix))
        return deleted

    def invalidate_after_product_sync(self, sync_status: str) -> int:
        """MVP invalidation for the Odoo -> PostgreSQL catalogue sync (task brief §9):
        precise per-changed-product invalidation would require sync_all() to thread a
        set of changed slugs/categories through six phases spanning categories,
        products, variants, prices, images, and stock — the task brief explicitly
        sanctions the coarser alternative ("acceptable for the MVP to invalidate the
        full catalogue product-list namespace after catalogue sync... prefer
        correctness over overly precise invalidation")."""
        if sync_status not in _SYNC_STATUSES_WORTH_INVALIDATING:
            logger.info(
                "cache_invalidation_skipped_sync_status",
                extra={
                    "cache_operation": "invalidate_after_product_sync",
                    "sync_status": sync_status,
                },
            )
            return 0
        deleted = self.invalidate_catalogue_all()
        logger.info(
            "cache_invalidated_after_product_sync",
            extra={
                "cache_operation": "invalidate_after_product_sync",
                "sync_status": sync_status,
                "cache_deleted_keys": deleted,
            },
        )
        return deleted

    def invalidate_after_merchandising_update(self, slug: str) -> int:
        """Featured/new/bestseller/visibility/display-order (task brief §10) — never
        touches categories/moments/recipients, since a single product's merchandising
        fields can't change those."""
        deleted = self.invalidate_product(slug)
        deleted += self.invalidate_homepage()
        deleted += self.invalidate_product_lists()
        logger.info(
            "cache_invalidated_after_merchandising_update",
            extra={
                "cache_operation": "invalidate_after_merchandising_update",
                "product_slug": slug,
                "cache_deleted_keys": deleted,
            },
        )
        return deleted
