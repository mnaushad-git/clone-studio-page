"""Cache-aside decorator over CatalogueQueryService (task brief §3, §4).

Kept as a separate wrapper rather than baking caching into CatalogueQueryService
itself, so the query service's business logic stays cache-agnostic (task brief §4:
"caching must remain outside core catalogue business rules where practical") — routes
call this instead of CatalogueQueryService directly; CatalogueQueryService is still
used unmodified for every write path and for cache misses here.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.api.v1.schemas.catalogue import (
    CategoryOut,
    HomepageOut,
    MomentOut,
    PaginatedProductsOut,
    ProductDetailOut,
    RecipientOut,
)
from app.cache import keys, metrics
from app.cache.interface import CacheClient
from app.cache.keys import ProductListFilters
from app.core.config import Settings
from app.services.catalogue.catalogue_query_service import CatalogueQueryService

logger = logging.getLogger("app.cache.catalogue_cache")

HIT = "HIT"
MISS = "MISS"
BYPASS = "BYPASS"
ERROR_FALLBACK = "ERROR-FALLBACK"

# Stampede-protection lock TTL for the homepage rebuild (task brief §12: "Lock TTL
# approximately 5-10 seconds"). Not applied to the cheaper categories/moments/
# recipients lookups or product detail — homepage is the one endpoint the brief calls
# out by name ("especially homepage") as expensive enough to warrant it.
_HOMEPAGE_LOCK_TTL_SECONDS = 8
_LOCK_WAIT_RETRIES = 5
_LOCK_WAIT_SECONDS = 0.1

T = TypeVar("T")

_CATEGORIES_ADAPTER: TypeAdapter[list[CategoryOut]] = TypeAdapter(list[CategoryOut])
_MOMENTS_ADAPTER: TypeAdapter[list[MomentOut]] = TypeAdapter(list[MomentOut])
_RECIPIENTS_ADAPTER: TypeAdapter[list[RecipientOut]] = TypeAdapter(list[RecipientOut])
_HOMEPAGE_ADAPTER: TypeAdapter[HomepageOut] = TypeAdapter(HomepageOut)
_PRODUCT_DETAIL_ADAPTER: TypeAdapter[ProductDetailOut] = TypeAdapter(ProductDetailOut)
_PAGINATED_PRODUCTS_ADAPTER: TypeAdapter[PaginatedProductsOut] = TypeAdapter(PaginatedProductsOut)


class CachedCatalogueQueryService:
    def __init__(self, session: Session, cache: CacheClient, settings: Settings) -> None:
        self.query = CatalogueQueryService(session)
        self._cache = cache
        self._settings = settings
        self._prefix = settings.cache_key_prefix

    # -- generic cache-aside read -----------------------------------------------

    def _cached(
        self,
        *,
        key: str,
        ttl_seconds: int,
        adapter: TypeAdapter[T],
        loader: Callable[[], T],
        stampede_protect: bool = False,
    ) -> tuple[T, str]:
        if not self._settings.cache_enabled:
            return loader(), BYPASS

        raw = self._cache.get_json(key)
        if raw is not None:
            try:
                value = adapter.validate_python(raw)
            except ValidationError as exc:
                logger.warning(
                    "cache_value_failed_validation",
                    extra={"cache_key_namespace": key.rsplit(":", 1)[0], "error": str(exc)},
                )
                self._cache.delete(key)
            else:
                metrics.record_hit()
                return value, HIT

        if not stampede_protect:
            value = loader()
            self._cache.set_json(key, adapter.dump_python(value, mode="json"), ttl_seconds)
            status = MISS if self._cache.ping() else ERROR_FALLBACK
            metrics.record_miss() if status == MISS else metrics.record_error()
            return value, status

        return self._cached_with_lock(
            key=key, ttl_seconds=ttl_seconds, adapter=adapter, loader=loader
        )

    def _cached_with_lock(
        self,
        *,
        key: str,
        ttl_seconds: int,
        adapter: TypeAdapter[T],
        loader: Callable[[], T],
    ) -> tuple[T, str]:
        lock_key = f"{key}:lock"
        token = self._cache.acquire_lock(lock_key, _HOMEPAGE_LOCK_TTL_SECONDS)
        if token is not None:
            try:
                value = loader()
                self._cache.set_json(key, adapter.dump_python(value, mode="json"), ttl_seconds)
            finally:
                self._cache.release_lock(lock_key, token)
            status = MISS if self._cache.ping() else ERROR_FALLBACK
            metrics.record_miss() if status == MISS else metrics.record_error()
            return value, status

        # Another request is already rebuilding this key — briefly wait and retry the
        # cache rather than piling another concurrent rebuild onto PostgreSQL (task
        # brief §12: "Other requests may briefly wait and retry cache").
        for _ in range(_LOCK_WAIT_RETRIES):
            time.sleep(_LOCK_WAIT_SECONDS)
            raw = self._cache.get_json(key)
            if raw is not None:
                try:
                    value = adapter.validate_python(raw)
                except ValidationError:
                    break
                metrics.record_hit()
                return value, HIT

        # Waiting would hurt availability past this point — serve PostgreSQL directly
        # without writing the cache ourselves (the lock holder owns that write).
        metrics.record_miss()
        return loader(), MISS

    # -- catalogue endpoints ------------------------------------------------------

    def list_categories(self) -> tuple[list[CategoryOut], str]:
        return self._cached(
            key=keys.categories_key(self._prefix),
            ttl_seconds=self._settings.cache_categories_ttl_seconds,
            adapter=_CATEGORIES_ADAPTER,
            loader=self.query.list_categories,
        )

    def list_moments(self) -> tuple[list[MomentOut], str]:
        return self._cached(
            key=keys.moments_key(self._prefix),
            ttl_seconds=self._settings.cache_moments_ttl_seconds,
            adapter=_MOMENTS_ADAPTER,
            loader=self.query.list_moments,
        )

    def list_recipients(self) -> tuple[list[RecipientOut], str]:
        return self._cached(
            key=keys.recipients_key(self._prefix),
            ttl_seconds=self._settings.cache_recipients_ttl_seconds,
            adapter=_RECIPIENTS_ADAPTER,
            loader=self.query.list_recipients,
        )

    def get_homepage(self) -> tuple[HomepageOut, str]:
        return self._cached(
            key=keys.homepage_key(self._prefix),
            ttl_seconds=self._settings.cache_homepage_ttl_seconds,
            adapter=_HOMEPAGE_ADAPTER,
            loader=self.query.get_homepage,
            stampede_protect=True,
        )

    def get_product_detail(self, slug: str) -> tuple[ProductDetailOut | None, str]:
        if not self._settings.cache_enabled:
            return self.query.get_product_detail(slug), BYPASS

        key = keys.product_detail_key(self._prefix, slug)
        raw = self._cache.get_json(key)
        if raw is not None:
            try:
                value = _PRODUCT_DETAIL_ADAPTER.validate_python(raw)
            except ValidationError:
                self._cache.delete(key)
            else:
                metrics.record_hit()
                return value, HIT

        detail = self.query.get_product_detail(slug)
        if detail is None:
            # Never cache a not-found result (task brief §3.6, §7).
            metrics.record_miss()
            return None, MISS
        self._cache.set_json(
            key,
            _PRODUCT_DETAIL_ADAPTER.dump_python(detail, mode="json"),
            self._settings.cache_product_detail_ttl_seconds,
        )
        status = MISS if self._cache.ping() else ERROR_FALLBACK
        metrics.record_miss() if status == MISS else metrics.record_error()
        return detail, status

    def list_products(
        self,
        *,
        category_slug: str | None = None,
        moment_slug: str | None = None,
        recipient_slug: str | None = None,
        featured: bool | None = None,
        is_bestseller: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[PaginatedProductsOut, str]:
        def loader() -> PaginatedProductsOut:
            return self.query.list_products(
                category_slug=category_slug,
                moment_slug=moment_slug,
                recipient_slug=recipient_slug,
                featured=featured,
                is_bestseller=is_bestseller,
                is_new=is_new,
                search=search,
                limit=limit,
                offset=offset,
            )

        if not self._settings.cache_enabled:
            return loader(), BYPASS

        filters = ProductListFilters(
            category=category_slug,
            moment=moment_slug,
            recipient=recipient_slug,
            featured=featured,
            bestseller=is_bestseller,
            new=is_new,
            search=search,
            limit=limit,
            offset=offset,
        )
        if not filters.is_cacheable():
            return loader(), BYPASS

        key = keys.product_list_key(self._prefix, filters)
        tracking_key = f"{keys.product_list_namespace_prefix(self._prefix)}_tracked"
        if not self._cache.sadd_bounded(
            tracking_key, filters.hash(), self._settings.cache_max_product_list_keys
        ):
            # Key-space cap reached — serve normally, just don't add another variant.
            return loader(), BYPASS

        return self._cached(
            key=key,
            ttl_seconds=self._settings.cache_product_list_ttl_seconds,
            adapter=_PAGINATED_PRODUCTS_ADAPTER,
            loader=loader,
        )
