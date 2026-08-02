# Redis — Local Development

## Starting Redis

Via Docker Compose (repository root):

```sh
docker compose up redis
```

Or a bare local Redis on the default port — `backend/.env.example`'s
`REDIS_URL=redis://localhost:6379/0` already matches.

Verify:

```sh
redis-cli ping   # PONG
```

## Disabling caching

Set `CACHE_ENABLED=false` in `backend/.env` (or the environment) and restart the API.
Every catalogue endpoint keeps working, reading PostgreSQL directly on every request —
useful when debugging whether a symptom is cache-related.

## Verifying cache hits

With `CACHE_DEBUG_HEADERS_ENABLED=true` (the default outside `APP_ENV=production`):

```sh
curl -i http://localhost:8000/api/v1/catalogue/homepage | grep -i x-cache
# X-Cache: MISS          (first request)
curl -i http://localhost:8000/api/v1/catalogue/homepage | grep -i x-cache
# X-Cache: HIT            (second request, within the TTL)
```

Or inspect Redis directly:

```sh
redis-cli --scan --pattern 'tb:v1:catalogue:*'
redis-cli GET tb:v1:catalogue:homepage:all
redis-cli TTL tb:v1:catalogue:homepage:all
```

## Clearing the cache safely

Preferred — through the app, so nothing outside `CacheInvalidationService` ever
issues a raw Redis command:

```sh
curl -X POST http://localhost:8000/api/v1/admin/system/cache/invalidate \
  -H "Content-Type: application/json" -H "X-CSRF-Token: <csrf>" \
  --cookie "<admin session cookie>" \
  -d '{"operation": "all"}'
```

(SUPER_ADMIN session required — see `docs/backend/admin-auth.md` if present, or log in
via `POST /api/v1/admin/auth/login`.)

Manual fallback (dev-only — never do this against a shared/prod Redis instance
casually, since `CACHE_KEY_PREFIX=tb` may share a Redis DB with Celery broker/result
backend keys on a different logical DB index, but not the same physical instance
unless misconfigured):

```sh
redis-cli --scan --pattern 'tb:v1:catalogue:*' | xargs -r redis-cli DEL
```

Or just wait — every cached entry has a bounded TTL (300s–900s) and self-expires.

## Troubleshooting stale values

1. Confirm the write path actually committed — cache invalidation only fires after a
   PostgreSQL commit (see [cache-invalidation.md](cache-invalidation.md)). Check the
   Odoo catalogue sync run's status (`GET /api/v1/admin/catalogue-sync/runs`) or the
   admin audit log for the merchandising PATCH.
2. Check the logs for `cache_invalidated_after_product_sync` /
   `cache_invalidated_after_merchandising_update` — absence means invalidation never
   ran (e.g. the sync run was marked `FAILED`, which correctly skips invalidation).
3. If invalidation ran but the value still looks stale, `GET` the key directly with
   `redis-cli` and compare against PostgreSQL — a serialization bug would show up as
   a mismatch here.
4. As a last resort, use the manual admin invalidate endpoint or `CACHE_ENABLED=false`
   to confirm PostgreSQL itself has the expected value, isolating the problem to the
   cache layer vs. the sync/update path.

## How Odoo sync and Admin changes invalidate cache

See [cache-invalidation.md](cache-invalidation.md) for the full contract — in short,
the Odoo-to-PostgreSQL catalogue sync task invalidates the whole catalogue namespace
once its run completes (only if not fully `FAILED`), and an Admin merchandising PATCH
invalidates that product's detail key, the homepage, and the product-list namespace,
immediately after its own commit.

## Test Redis isolation

`backend/tests/conftest.py` points `REDIS_URL` at db 15 during tests (separate from
the dev DB 0) and flushes it before/after every test that uses the `db_session`
fixture, so cache state from one test can never leak into another.
