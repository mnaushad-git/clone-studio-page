# Backend Environment Variables

Defined in `backend/app/core/config.py` (`Settings`, `pydantic-settings`). Local
values live in `backend/.env` (untracked — copy from `backend/.env.example`).
Docker Compose sets container-network values (`postgres`/`redis` hostnames)
directly in `docker-compose.yml` and does not read `backend/.env`.

| Variable | Purpose | Default (non-Docker) |
|---|---|---|
| `APP_NAME` | Application display name | `Terrific Bites API` |
| `APP_VERSION` | Reported by `/api/v1/version` | `0.1.0` |
| `APP_ENV` | `development` \| `test` \| `production` — gates `/docs`/`/redoc` | `development` |
| `DEBUG` | Verbose-mode flag (not yet wired to a behavior beyond being available) | `false` |
| `API_V1_PREFIX` | Route prefix for all v1 routes | `/api/v1` |
| `HOST` | Bind host for the ASGI server | `0.0.0.0` |
| `PORT` | Bind port for the ASGI server | `8000` |
| `LOG_LEVEL` | Root logger level | `INFO` |
| `DATABASE_URL` | SQLAlchemy connection string (`postgresql+psycopg://...`) | localhost Postgres |
| `DATABASE_POOL_SIZE` | SQLAlchemy engine pool size | `5` |
| `DATABASE_MAX_OVERFLOW` | SQLAlchemy engine max overflow | `10` |
| `REDIS_URL` | Redis connection string (cache) | localhost Redis db 0 |
| `CELERY_BROKER_URL` | Celery broker (Redis) | localhost Redis db 1 |
| `CELERY_RESULT_BACKEND` | Celery result backend (Redis) | localhost Redis db 2 |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `TRUSTED_HOSTS` | Comma-separated allowed `Host` header values | `localhost,127.0.0.1` |
| `ODOO_BASE_URL` | Odoo instance URL — read by `app/integrations/odoo/config.py` (Phase 4) | empty |
| `ODOO_DATABASE` | Odoo database name | empty |
| `ODOO_USERNAME` | Odoo login username | empty |
| `ODOO_PASSWORD` | Odoo password — set this **or** `ODOO_API_KEY`, never both; never logged | empty |
| `ODOO_API_KEY` | Odoo API key — alternative to `ODOO_PASSWORD`; never logged | empty |
| `ODOO_TIMEOUT_SECONDS` | Per-request timeout (seconds) | `30` |
| `ODOO_VERIFY_SSL` | Verify TLS certificates on the Odoo connection | `true` |
| `ODOO_MAX_RETRIES` | Bounded retry count for read-only calls only | `3` |
| `ODOO_RETRY_BACKOFF_SECONDS` | Base backoff between retries (doubles per attempt) | `1.0` |
| `ODOO_READ_BATCH_SIZE` | Default page size for `search_read`/pagination | `200` |
| `ODOO_PROTOCOL` | Integration protocol — only `jsonrpc` is supported (see [odoo-client.md](../integrations/odoo-client.md)) | `jsonrpc` |
| `ODOO_COMPANY_ID` | Optional — target a specific company in a multi-company instance | empty (auto-selects the first company) |
| `ODOO_DEFAULT_PRICELIST_ID` | Optional — default sales pricelist id | empty |
| `ODOO_DEFAULT_WAREHOUSE_ID` | Optional — default warehouse id | empty |
| `CACHE_ENABLED` | Master on/off switch for catalogue Redis caching — see [redis-caching.md](redis-caching.md) | `true` |
| `CACHE_KEY_PREFIX` | Namespace prefix for every cache key | `tb` |
| `CACHE_HOMEPAGE_TTL_SECONDS` | TTL for `GET /catalogue/homepage` | `300` |
| `CACHE_CATEGORIES_TTL_SECONDS` | TTL for `GET /catalogue/categories` | `900` |
| `CACHE_PRODUCT_DETAIL_TTL_SECONDS` | TTL for `GET /catalogue/products/{slug}` | `300` |
| `CACHE_MOMENTS_TTL_SECONDS` | TTL for `GET /catalogue/moments` | `900` |
| `CACHE_RECIPIENTS_TTL_SECONDS` | TTL for `GET /catalogue/recipients` | `900` |
| `CACHE_PRODUCT_LIST_TTL_SECONDS` | TTL for `GET /catalogue/products` (list) | `120` |
| `CACHE_REDIS_OPERATION_TIMEOUT_SECONDS` | Socket timeout for the dedicated cache Redis client | `1` |
| `CACHE_MAX_PRODUCT_LIST_KEYS` | Soft cap on distinct cached product-list filter combinations | `500` |
| `CACHE_LOG_HITS` | Log every cache hit/miss (noisy — off by default) | `false` |
| `CACHE_COMPRESSION_ENABLED` | Reserved; no compression codec is implemented yet | `false` |
| `CACHE_DEBUG_HEADERS_ENABLED` | Emit `X-Cache`/`X-Cache-Key-Version` response headers (never in `APP_ENV=production`) | `true` |

Leaving `ODOO_BASE_URL`/`ODOO_DATABASE`/`ODOO_USERNAME` all empty keeps Odoo
unconfigured — the app starts normally either way; `verify_odoo_connection` reports
`BLOCKED` with an explicit reason rather than failing silently. See
[odoo-operations-runbook.md](../integrations/odoo-operations-runbook.md).

## Secrets

- `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`,
  `ODOO_PASSWORD`, and `ODOO_API_KEY` are treated as secret fields:
  `Settings.masked_dict()` (used in the one startup log line) redacts them, and
  `core/logging.py`'s `SecretRedactionFilter` scrubs their literal values out of any
  other log message that might contain them.
- Never commit `backend/.env`. Only `backend/.env.example` (placeholder values) is
  tracked.
