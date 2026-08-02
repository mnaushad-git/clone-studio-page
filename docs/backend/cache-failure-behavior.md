# Cache Failure Behavior

PostgreSQL is always the fallback. No catalogue endpoint returns 500 solely because
Redis is unavailable, slow, or holding a corrupt value.

## Guarantees

`RedisCache` (`backend/app/cache/redis_cache.py`) catches every Redis/serialization
failure itself — `get_json`, `set_json`, `delete`, `delete_many`, `delete_by_prefix`,
`exists`, `ping`, `acquire_lock`, `sadd_bounded` never raise. Callers (the cache-aside
wrapper, the invalidation service) never need their own try/except around a cache
call.

| Scenario | Behavior |
|---|---|
| Redis unavailable at startup | App starts normally; `RedisCache` connects lazily, first call fails safely |
| Redis becomes unavailable mid-request | `get_json`/`set_json` catch `redis.RedisError`, return `None`/`False`; endpoint falls through to PostgreSQL |
| Redis GET/SET timeout | `CACHE_REDIS_OPERATION_TIMEOUT_SECONDS` (default 1s) bounds the wait; treated the same as unavailable |
| Invalid/corrupt cached JSON | `get_json` catches the decode error, deletes the corrupt key, returns `None` (next request rebuilds cleanly) |
| Redis returns an unexpected type | Same corrupt-value path — deleted, logged, falls through |
| Prefix invalidation fails mid-SCAN | Partial deletion count is still returned/logged; a sync/merchandising commit that already succeeded is never rolled back over this |
| Redis recovers | Next request after recovery caches normally again — no manual intervention needed |

## Response header when Redis fails after a successful DB read

`X-Cache: ERROR-FALLBACK` (non-production only) — the response body is correct
(built from PostgreSQL), but the `set_json` that should have cached it failed. This
is distinguished from a normal `MISS` by one extra `PING` after a failed write.

## What must never happen

- A catalogue endpoint returning 500 because Redis is down.
- A cache miss silently returning nothing (empty list/null) instead of falling
  through to PostgreSQL — `CachedCatalogueQueryService` always calls the real
  `CatalogueQueryService` loader on a miss, cache-error, or corrupt value.
- Caching a not-found (404) product-detail result, or any non-2xx response.
- Redis values being treated as authoritative for order creation, checkout,
  payment, or inventory decisions — nothing outside `app/cache/` and the catalogue
  read path touches `RedisCache` at all.

## Readiness / health

`GET /api/v1/readiness` and the Admin system-status endpoint's `redis` field already
report Redis connectivity independently of catalogue caching (Celery/admin-login-
throttle also depend on Redis) — a Redis outage is visible operationally even though
it never breaks a catalogue response. The process-only `/health` endpoint is
unaffected either way.

## Verified by

`backend/tests/integration/test_cache_redis.py::test_get_json_unavailable_redis_falls_back_to_none`
and `test_corrupt_cached_value_is_deleted_and_returns_none`;
`backend/tests/integration/test_catalogue_cache_api.py::test_redis_unavailable_falls_back_to_postgres`
(full endpoint-level proof: 200 with correct data, `X-Cache: ERROR-FALLBACK`, Redis
pointed at an unreachable host).
