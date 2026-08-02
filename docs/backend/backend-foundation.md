# Backend Foundation (Phase 1)

_Status: implemented. Scope: `backend/` scaffold only — no business modules
(catalogue, cart, checkout, orders, admin/customer auth) exist yet. Corresponds to
[implementation-roadmap.md](../architecture/implementation-roadmap.md) step 1, plus
the Postgres/Redis/Celery-container plumbing pulled forward from step 2 at the
requester's explicit direction (Docker Compose services, connectivity checks) —
without step 2's domain migrations, which remain future work._

## What this phase delivers

- **Application bootstrap** — `app/main.py` app factory (`create_app()`), building
  middleware, exception handlers, and routers in one place.
- **Environment-based configuration** — `app/core/config.py`, a `pydantic-settings`
  `Settings` class reading every variable listed in
  [environment-variables.md](environment-variables.md), with `.env` support and a
  `masked_dict()` helper that redacts secret fields before they're logged.
- **PostgreSQL connection/session management** — `app/core/database.py`: a pooled
  SQLAlchemy 2.x engine, `get_db()` FastAPI dependency, `session_scope()` context
  manager for non-request code (workers/scripts), `check_database_connection()` for
  readiness.
- **SQLAlchemy declarative base** — `Base` in `app/core/database.py`, imported by
  Alembic's `env.py`; no ORM models exist yet.
- **Alembic migration framework** — `backend/alembic.ini` (script location
  `app/db/alembic`, no connection string committed to the file — `env.py` reads
  `Settings.database_url` instead) plus one baseline revision (`0001_baseline`)
  that creates no tables, per the "no business tables yet" constraint.
- **Redis connection configuration** — `app/core/redis.py`: a cached client factory
  and `check_redis_connection()` for readiness.
- **Celery worker foundation** — `app/workers/celery_app.py`, broker/result-backend
  from settings, JSON serialization, one smoke-test task
  (`app/workers/tasks/health.py::ping`) proving worker wiring end-to-end.
- **Celery Beat scheduler foundation** — same Celery app, `beat_schedule={}` (empty
  — populated once sync tasks land per
  [component-view.md](../architecture/component-view.md) §4).
- **API versioning** — every route under `/api/v1` (`app/api/v1/router.py`,
  prefix from `Settings.api_v1_prefix`).
- **Standard API response/error conventions** — `app/core/errors.py`: every
  non-2xx response is `{"error": {"code", "message", "correlation_id", "details"?}}`
  per [api-standards.md](../architecture/api-standards.md) §4.
- **Global exception handling** — `AppError` subclasses, `RequestValidationError`,
  Starlette `HTTPException`, and any unhandled `Exception` are all mapped to the
  same envelope by `register_exception_handlers()`.
- **Request correlation ID middleware** — `app/core/middleware.py`:
  `CorrelationIdMiddleware` reads `X-Correlation-ID` if present and valid,
  otherwise generates `req_<uuid4hex>`; always echoed back in the response header.
- **Structured JSON logging** — `app/core/logging.py`: one JSON line per log
  record (`timestamp`, `level`, `correlation_id`, `module`, `event`, plus extras),
  applied to both `app.*` and `uvicorn.*` loggers.
- **Request-duration logging** — `RequestLoggingMiddleware` logs
  `http_request_completed` with method, path, status code, and duration in ms.
- **CORS configuration** — `Settings.cors_allowed_origins`, comma-separated in the
  environment, parsed to a list.
- **Trusted-host configuration** — `Settings.trusted_hosts`, same pattern, enforced
  by Starlette's `TrustedHostMiddleware`.
- **Health / readiness / version endpoints** — see below.
- **Basic DB/Redis connectivity checks** — `check_database_connection()` /
  `check_redis_connection()`, used only by `/readiness`, never by `/health`.
- **Dependency-injection foundation** — `app/dependencies.py`: `get_db`, `get_redis`,
  `get_app_settings`.
- **Test configuration** — `backend/tests/conftest.py` + `pytest.ini_options` in
  `pyproject.toml`.
- **Dockerfile / Docker Compose / env template** — see
  [local-development.md](local-development.md).

## Endpoints

| Method | Path | Purpose | Depends on |
|---|---|---|---|
| GET | `/api/v1/health` | Liveness — process is running | nothing (no DB/Redis calls) |
| GET | `/api/v1/readiness` | PostgreSQL + Redis reachability | PostgreSQL, Redis |
| GET | `/api/v1/version` | App version, environment, API version | nothing |

`/readiness` returns `200` with `"status": "ok"` when both dependencies are
reachable, or `503` with `"status": "unavailable"` and a per-dependency status
(`"ok"` / `"unavailable"`) otherwise — it never raises for a normal storefront
request per architecture rule 6 (Odoo/DB unavailability doesn't block this check's
own response, it's reported as data).

## What was intentionally not built

Per the explicit Phase 1 constraints: no products/categories, no Odoo client (only
config placeholders), no catalogue sync, no cart/checkout/orders, no
customer/admin authentication, no business ORM models or domain migrations, no
frontend wiring beyond adding the unused `VITE_API_BASE_URL` variable. These are
scoped to later roadmap steps.

## Deviations / conflicts from the architecture docs

- The task's suggested file tree used `services/api/` as the backend root; this
  was overridden in favor of `backend/` at the repo root, since
  [target-architecture.md](../architecture/target-architecture.md) §7 and
  [implementation-roadmap.md](../architecture/implementation-roadmap.md) step 1
  explicitly specify that path, and the task itself said to adjust the suggested
  tree only where the approved architecture requires it.
- No other structural deviation. `app/modules/` (business module packages) is not
  created yet — it doesn't exist until the first business module needs it, per the
  "no premature scaffolding" principle in
  [target-architecture.md](../architecture/target-architecture.md) §4.
