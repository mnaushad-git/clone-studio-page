# Terrific Bites API (backend)

FastAPI modular monolith. Phase 1 (Backend Foundation), Phase 3 (PostgreSQL Catalogue
Foundation), Phase 4 (Odoo Environment Verification + read-only client), and Phase 5
(Controlled Odoo Catalogue Import Foundation) are implemented; cart, checkout, orders,
auth, recurring catalogue sync, and catalogue API endpoints do not exist yet. See
[docs/architecture/implementation-roadmap.md](../docs/architecture/implementation-roadmap.md).

## What's here

- FastAPI app factory, `/api/v1` routing, standard error envelope, global exception
  handling.
- Correlation-ID middleware + structured JSON logging + request-duration logging.
- SQLAlchemy 2.x engine/session plumbing, Alembic baseline (`0001`) + the catalogue
  schema (`0002`) — 16 tables covering categories, products, variants, prices,
  availability, images, merchandising, storefront sections, moments, recipients, and
  sync/seed metadata. See
  [docs/backend/postgresql-catalogue-schema.md](../docs/backend/postgresql-catalogue-schema.md).
- A repository layer (`app/repositories/`) and an idempotent catalogue seed service
  (`app/services/catalogue/`, run via `python -m app.scripts.seed_catalogue`) that
  loads the canonical `data/catalogue/*.json` files. See
  [docs/backend/catalogue-seeding.md](../docs/backend/catalogue-seeding.md).
- Redis client plumbing, plus a cache-aside acceleration layer (`app/cache/`) over the
  five read-heavy catalogue endpoints (homepage, categories, product detail, moments,
  recipients) and the optional product-list endpoint. PostgreSQL stays authoritative
  and every endpoint keeps working with `CACHE_ENABLED=false` or Redis stopped
  outright. See [docs/backend/redis-caching.md](../docs/backend/redis-caching.md).
- Celery app + Celery Beat foundation, including the Odoo catalogue pull sync
  (`app.workers.tasks.catalogue_sync`), which invalidates the catalogue cache after
  each successful/partially-successful run.
- `GET /api/v1/health`, `GET /api/v1/readiness`, `GET /api/v1/version`.
- A read-only Odoo integration client (`app/integrations/odoo/`) — JSON-RPC transport,
  authentication, metadata/capability discovery, per-model repositories, and
  evidence-based catalogue field-mapping. No write methods are exposed (`create`/
  `write`/`unlink`/etc. are structurally rejected). Two CLIs:
  `python -m app.scripts.verify_odoo_connection` and
  `python -m app.scripts.plan_odoo_catalogue_import` (dry-run only — never imports).
  See [docs/integrations/](../docs/integrations/), starting with
  [odoo-client.md](../docs/integrations/odoo-client.md). No product/catalogue API
  endpoints exist yet — the FastAPI layer doesn't read from the catalogue tables this
  phase, and no Odoo write has been performed against any instance yet.
- A controlled, write-capable Odoo catalogue importer (Phase 5) — a business approval
  gate (`data/catalogue/catalogue-business-approvals.json` +
  `python -m app.scripts.check_catalogue_import_approvals`), a separate write-capable
  client (`app/integrations/odoo/write_client.py`) with a closed model/method
  allowlist, PostgreSQL import-run/item audit tables (Alembic `0003`), and a five-mode
  CLI: `python -m app.scripts.import_odoo_catalogue --validate|--plan|--dry-run|
  --apply|--reconcile`, plus `python -m app.scripts.plan_odoo_catalogue_rollback`.
  **`--apply` is currently refused** — five business decisions
  (`D03`/`D04`/`D08`/`D10`/`D19`) remain unapproved. See
  [docs/integrations/odoo-catalogue-import.md](../docs/integrations/odoo-catalogue-import.md)
  and [docs/integrations/odoo-import-runbook.md](../docs/integrations/odoo-import-runbook.md).

## Local development — without Docker

Requires Python 3.12.

```sh
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

cp .env.example .env            # then edit values as needed (never commit .env)

ruff format --check .
ruff check .
mypy app
pytest

# Requires a reachable PostgreSQL matching DATABASE_URL in .env
alembic upgrade head

# Optional: load the canonical catalogue data (see docs/backend/catalogue-seeding.md)
python -m app.scripts.seed_catalogue --dry-run
python -m app.scripts.seed_catalogue --apply

# Optional: verify Odoo connectivity (requires ODOO_* set in .env — see
# docs/integrations/odoo-operations-runbook.md; reports BLOCKED if unconfigured)
python -m app.scripts.verify_odoo_connection
python -m app.scripts.plan_odoo_catalogue_import

# Optional: Phase 5 controlled Odoo catalogue import (never runs --apply without
# separate, explicit confirmation — see docs/integrations/odoo-import-runbook.md)
python -m app.scripts.check_catalogue_import_approvals
python -m app.scripts.import_odoo_catalogue --validate
python -m app.scripts.import_odoo_catalogue --plan
python -m app.scripts.import_odoo_catalogue --dry-run

uvicorn app.main:app --reload
```

Then:

```sh
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/version
curl http://localhost:8000/api/v1/readiness   # 200 if Postgres+Redis reachable, else 503
```

## Local development — with Docker Compose

From the repository root (`docker-compose.yml` lives there, not under `backend/`):

```sh
docker compose up --build
```

Starts `postgres`, `redis`, `backend-api` (port `8000` by default, override with
`API_PORT`), `celery-worker`, `celery-beat`. See
[../docs/backend/local-development.md](../docs/backend/local-development.md) for
details, including running migrations inside the container.

## Tests

Most of the suite runs fully offline: readiness success/failure paths are exercised by
monkeypatching the connectivity-check functions rather than requiring a live
Postgres/Redis, and the entire Odoo integration suite (`tests/unit/odoo/`) runs
against a fake transport double, never a real network call. Catalogue model/
repository/seed tests are the exception — they need a real, reachable PostgreSQL
(never SQLite; see
[docs/backend/catalogue-testing.md](../docs/backend/catalogue-testing.md) and
[../docs/architecture/testing-strategy.md](../docs/architecture/testing-strategy.md)).
Opt-in, real-Odoo integration tests (`tests/integration/test_odoo_integration.py`) are
disabled unless `RUN_ODOO_INTEGRATION_TESTS=1` is set and Odoo is configured — see
[docs/integrations/odoo-testing.md](../docs/integrations/odoo-testing.md).

Cache tests (`tests/unit/test_cache_*.py`, `tests/integration/test_cache_*.py`,
`tests/integration/test_catalogue_cache_api.py`) run against a real, reachable Redis
at `REDIS_URL` (test default: db 15 — see `tests/conftest.py`). The `db_session`
fixture flushes that DB before/after every test that uses it, so cache state never
leaks between tests. See
[docs/backend/redis-local-development.md](../docs/backend/redis-local-development.md).

## Environment variables

See [.env.example](.env.example) and
[../docs/backend/environment-variables.md](../docs/backend/environment-variables.md).
