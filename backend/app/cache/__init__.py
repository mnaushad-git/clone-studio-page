"""Cache-aside Redis acceleration layer for the read-heavy catalogue endpoints.

PostgreSQL remains authoritative (CLAUDE.md rule 2) — every function here is purely an
acceleration layer over app/services/catalogue/catalogue_query_service.py. Redis is
never used as an authoritative input for order creation, checkout, payment, or
inventory decisions, and every catalogue endpoint keeps serving correct data with
CACHE_ENABLED=false or Redis stopped outright (see cache_failure_behavior in
docs/backend/redis-caching.md).
"""

from __future__ import annotations

from functools import lru_cache

from app.cache.redis_cache import RedisCache
from app.core.config import get_settings


@lru_cache
def get_cache_client() -> RedisCache:
    """Process-wide singleton, mirroring app.core.redis.get_redis_client's pattern."""
    return RedisCache(get_settings())


__all__ = ["RedisCache", "get_cache_client"]
