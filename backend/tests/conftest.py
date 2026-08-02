"""Test configuration.

Environment variables are set before `app.main` is imported so the app is built
with predictable test values (in particular TRUSTED_HOSTS must include
"testserver", the Host header httpx.TestClient sends by default).

Most of this suite runs fully offline: the readiness tests monkeypatch the
connectivity-check functions at their call site rather than depending on real
infrastructure being reachable. Catalogue model/repository/seed tests are the
exception (Phase 3) — they use the `db_session` fixture below, which requires a
real, reachable PostgreSQL database at DATABASE_URL (never SQLite — constraint,
JSONB, and partial-index behaviour tested here are PostgreSQL-specific, per
docs/architecture/testing-strategy.md). The DATABASE_URL default below matches
docker-compose.yml's own postgres/postgres dev credentials, not a real secret;
override it in your shell/local .env if your local Postgres uses a different
password — never hardcode a real one here.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/terrific_bites_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver")
# Force Odoo "not configured" for the whole suite, regardless of what a developer's
# .env has set for real local-Odoo development (Settings reads .env, and env vars take
# priority over it — see app/core/config.py) — except when test_odoo_integration.py's
# explicitly opt-in live suite is what's being run (RUN_ODOO_INTEGRATION_TESTS=1), which
# needs the real credentials to do its job. Without this, OdooConfig.is_configured()
# sees real credentials and _connect_readonly() makes a genuine network call to
# whatever Odoo instance ODOO_BASE_URL points at; if one happens to be reachable (e.g.
# a developer's local Odoo for manual testing), a "sync now" test dispatches a real,
# permanently-committed (session_scope(), not covered by db_session's rollback) pull of
# that instance's actual category/product data into the test database — corrupting
# later tests in the same run with real rows (e.g. a genuine "Cupcakes" category
# colliding with a test's own `make_category(slug="cupcakes")`).
if os.environ.get("RUN_ODOO_INTEGRATION_TESTS") != "1":
    os.environ["ODOO_BASE_URL"] = ""
    os.environ["ODOO_DATABASE"] = ""
    os.environ["ODOO_USERNAME"] = ""

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
import redis  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.cache import get_cache_client  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.workers.celery_app import celery_app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent

# The suite must never depend on a real Redis broker being reachable: eager mode runs
# a .delay()'d task synchronously in-process instead of publishing it (same mechanism
# test_worker_foundation.py demonstrates per-test), so any endpoint that enqueues a
# task — e.g. POST /orders/{id}/pay's push_paid_orders_to_odoo.delay() — stays testable
# without a broker running. Production always uses the real broker; this is test-only.
celery_app.conf.task_always_eager = True


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def flush_cache() -> Generator[None, None, None]:
    """Flushes the test Redis cache DB (REDIS_URL=.../15, distinct from the real
    dev/prod DB 0) before and after each cache test — Redis state is not covered by
    db_session's per-test rollback, so it needs its own isolation."""
    test_redis = redis.Redis.from_url(get_settings().redis_url)
    test_redis.flushdb()
    get_cache_client.cache_clear()
    yield
    test_redis.flushdb()


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Applies every Alembic migration to DATABASE_URL once per test session, then
    hands back a plain engine. Requires a real, reachable PostgreSQL — see module
    docstring.
    """
    settings = get_settings()
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "app" / "db" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")

    engine = create_engine(settings.database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine, flush_cache: None) -> Generator[Session, None, None]:
    """One outer, never-committed transaction per test. `join_transaction_mode=
    "create_savepoint"` means even a `session.commit()` inside the code under test
    (the seed service commits its audit row, for instance) only releases a SAVEPOINT
    rather than the real transaction — so every test's writes are fully undone by the
    final rollback, regardless of how many commits happened inside it.

    Depends on `flush_cache` so every test that touches Postgres through this fixture
    also gets a clean Redis cache DB — a catalogue endpoint hit in one test would
    otherwise leave a HIT-able cache entry that a later, unrelated test could read
    back as if it were its own (fully-offline, non-db_session) unit tests never touch
    Redis and don't pay this cost.
    """
    connection = db_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
