# Redis Catalogue Caching

Cache-aside acceleration layer over the read-heavy `GET /api/v1/catalogue/*`
endpoints. PostgreSQL remains the storefront's operational runtime database and the
serving source of truth (CLAUDE.md rule 2); Redis is purely an acceleration layer —
never an authoritative input for order creation, checkout, payment, or inventory
decisions, and never written to before the PostgreSQL transaction that produced the
data has committed.

See also: [cache-key-conventions.md](cache-key-conventions.md),
[cache-invalidation.md](cache-invalidation.md),
[cache-failure-behavior.md](cache-failure-behavior.md),
[cache-performance-results.md](cache-performance-results.md),
[redis-local-development.md](redis-local-development.md).

## Cached endpoints

| Endpoint | TTL setting | Default |
|---|---|---|
| `GET /catalogue/homepage` | `CACHE_HOMEPAGE_TTL_SECONDS` | 300s |
| `GET /catalogue/categories` | `CACHE_CATEGORIES_TTL_SECONDS` | 900s |
| `GET /catalogue/products/{slug}` | `CACHE_PRODUCT_DETAIL_TTL_SECONDS` | 300s |
| `GET /catalogue/moments` | `CACHE_MOMENTS_TTL_SECONDS` | 900s |
| `GET /catalogue/recipients` | `CACHE_RECIPIENTS_TTL_SECONDS` | 900s |
| `GET /catalogue/products` (list) | `CACHE_PRODUCT_LIST_TTL_SECONDS` | 120s, bounded key space |

## Deliberately not cached

Cart, checkout calculations, promo-code validation, delivery-slot capacity, customer
profile, customer orders, admin order details, payment status, Odoo order-sync status,
notification status, authentication (storefront or admin), or any response containing
private customer information. None of these are touched by `app/cache/` — the module
only wraps `CatalogueQueryService` (see `app/cache/catalogue_cache.py`).

## Architecture

```
Route handler (app/api/v1/endpoints/catalogue.py)
    -> CachedCatalogueQueryService (app/cache/catalogue_cache.py)
        -> cache hit:  RedisCache.get_json(key)              -> return
        -> cache miss: CatalogueQueryService(session).<method>() -> RedisCache.set_json(...) -> return
```

Route handlers never construct Redis commands directly — they call
`CachedCatalogueQueryService`, which is the only thing that talks to `RedisCache`.
`CatalogueQueryService` itself is completely unmodified and cache-agnostic; caching
lives entirely in the decorator, not in catalogue business logic.

### Cache abstraction (`app/cache/`)

| File | Purpose |
|---|---|
| `interface.py` | `CacheClient` Protocol — `get_json`/`set_json`/`delete`/`delete_many`/`delete_by_prefix`/`exists`/`ping`/`acquire_lock`/`release_lock`/`sadd_bounded` |
| `redis_cache.py` | `RedisCache` — the only production implementation, backed by a dedicated `redis.Redis` client (`CACHE_REDIS_OPERATION_TIMEOUT_SECONDS`, separate from the shared client Celery/admin-login-throttle use) |
| `serializer.py` | Stdlib-`json`-based codec: Decimal/UUID/datetime/date encode as strings, Arabic/Unicode stored as literal UTF-8 |
| `keys.py` | Deterministic key builders + product-list filter normalization/hashing |
| `invalidation.py` | `CacheInvalidationService` — the single call site for every catalogue cache invalidation |
| `catalogue_cache.py` | `CachedCatalogueQueryService` — the cache-aside decorator routes call |
| `metrics.py` | Approximate, process-local hit/miss/error counters (Admin system-status) |

### Configuration

`CACHE_ENABLED=false` bypasses Redis completely for every catalogue endpoint — normal
PostgreSQL reads continue unaffected. See
[environment-variables.md](environment-variables.md) for the full `CACHE_*` list.

## Stampede protection

`GET /catalogue/homepage` (the most expensive cached endpoint) uses a short Redis
lock (`SET NX PX`, ~8s TTL) around a cache-miss rebuild: the first request to miss
acquires the lock and rebuilds; concurrent requests that lose the race briefly
retry the cache (3 x 100ms) and, if the rebuild still isn't visible, fall back to
querying PostgreSQL directly themselves rather than blocking. A crashed rebuild can
never leave a permanent lock — it simply expires. See `_cached_with_lock` in
`app/cache/catalogue_cache.py`.

## Observability

Non-production only (`APP_ENV != production` and `CACHE_DEBUG_HEADERS_ENABLED=true`,
the default), every cached response carries:

```
X-Cache: HIT | MISS | BYPASS | ERROR-FALLBACK
X-Cache-Key-Version: v1
```

`ERROR-FALLBACK` means the response is correct (served from PostgreSQL) but the
Redis write that should have followed it failed — distinguishable from a normal
`MISS` by pinging Redis once after a failed `set_json`. Never exposes a Redis
hostname, port, or credential.

Structured log fields on every cache operation: `cache_operation`,
`cache_key_namespace`, `cache_latency_ms`, `cache_error` (on failure),
`cache_deleted_keys` (on prefix invalidation). `CACHE_LOG_HITS=true` additionally logs
every individual hit/miss (off by default — noisy). Cached response bodies are never
logged.

## Admin visibility

`GET /api/v1/admin/system/status` reports `cache_enabled`, `cache_key_version`, and
approximate `cache_hits`/`cache_misses`/`cache_errors` counters (process-local, reset
on restart) alongside existing Redis/Celery/Odoo status fields.

`POST /api/v1/admin/system/cache/invalidate` (SUPER_ADMIN only, CSRF-protected,
audited) lets an operator invalidate `homepage` | `categories` | `product` (+`slug`)
| `moments` | `recipients` | `product_lists` | `all` without a backend restart or
raw Redis access. See [cache-invalidation.md](cache-invalidation.md).
