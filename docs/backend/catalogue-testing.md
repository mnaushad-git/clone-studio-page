# Catalogue Testing

Phase 3 is the first phase to need a real PostgreSQL-backed test fixture — everything
before it ran fully offline (readiness tests monkeypatch connectivity checks). This is
expected; see `backend/README.md`'s original Phase 1 note.

## Fixtures (`backend/tests/conftest.py`)

- **`db_engine`** (session-scoped) — runs `alembic upgrade head` against
  `DATABASE_URL` once per test session, then hands back a plain `Engine`. Requires a
  real, reachable PostgreSQL database — **never falls back to SQLite** (constraint,
  `JSONB`, and partial-index behaviour tested here are PostgreSQL-specific, per
  [testing-strategy.md](../architecture/testing-strategy.md)).
- **`db_session`** (function-scoped) — one connection, one outer transaction
  (`connection.begin()`), and a `Session` bound to it with
  `join_transaction_mode="create_savepoint"`. This is the key detail: any
  `session.commit()` that happens *inside* the code under test (the seed service
  commits its `catalogue_seed_runs` audit row every run, including dry-runs) only
  releases a `SAVEPOINT`, not the real transaction. The fixture's final
  `trans.rollback()` always undoes everything, regardless of how many commits happened
  inside the test. Tests that expect an `IntegrityError` (constraint violations) call
  `db_session.rollback()` afterward to recover the session for further use in the same
  test — that rolls back to the savepoint, not the whole transaction.

`DATABASE_URL`'s committed default (`postgres:postgres@localhost:5432/terrific_bites_test`)
matches `docker-compose.yml`'s own dev credentials — not a real secret. Override it via
your shell or an untracked `backend/.env` if your local PostgreSQL uses a different
password; never hardcode a real one into `conftest.py`.

## Test files

| File | Covers |
|---|---|
| `tests/integration/catalogue_factories.py` | `make_category`/`make_product` — minimal-field builders, not a pytest file itself |
| `tests/integration/test_catalogue_model_constraints.py` | Every DB-enforced constraint: unique external_key/sku/slug, required + valid category FK, no-self-recommend, one merchandising row per product, duplicate section-product mapping rejected, one default variant per product, one active price per variant+currency, non-negative price, `price_includes_tax` defaults null, valid availability_status, no self-parenting category |
| `tests/integration/test_catalogue_repositories.py` | `get_by_id` (miss), `get_by_sku`, `get_by_external_key`, `list_active`, and the `upsert_by_external_key` created→updated→no-op sequence |
| `tests/integration/test_catalogue_seed_service.py` | Dry-run writes nothing, first seed's exact counts, second seed is a full idempotent no-op, changed canonical values propagate as updates (not false creates), null Arabic preserved, zero fake inventory, `price_includes_tax` always null, rollback on an invalid reference, seed-run history recorded |
| `tests/integration/test_catalogue_migration.py` | `alembic upgrade head` → `downgrade 0001` → `upgrade head` round-trip against real PostgreSQL, self-contained (own engine, restores to head in `finally` so it can't leave other tests' schema in a bad state) |

The seed-service tests run against the **real canonical `data/catalogue/*.json`
files** for most cases (so their assertions double as a live check that the current
canonical data still matches the documented counts), and monkeypatch
`seed_service.load_catalogue_seed_data` only for the two cases that need synthetic
data: a changed-value update and an invalid-reference failure.

## Running

```bash
cd backend
# Point at your local Postgres if it differs from the docker-compose default:
export DATABASE_URL="postgresql+psycopg://postgres:<password>@127.0.0.1:5432/terrific_bites_test"
pytest
```

CI (`.github/workflows/backend-ci.yml`) runs the same suite against a `postgres:16`
service container — no local override needed there.
