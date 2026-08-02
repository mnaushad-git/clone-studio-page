# Odoo Integration Testing

## Mocked tests (always run, no external dependency)

`backend/tests/unit/odoo/` — 81 tests, all against a `FakeTransport` test double
(`conftest.py`) implementing the same `.call(service, method, args, *, retryable,
correlation_id)` surface as the real `OdooTransport`. No network call, no real Odoo
instance, no Postgres. Runs as part of the normal suite:

```
cd backend
pytest tests/unit/odoo -q
```

Coverage: configuration validation and secret redaction (`test_config.py`,
`test_exceptions.py`), transport retry/backoff/error-translation
(`test_transport.py`), authentication success/failure
(`test_authentication.py`), read-only enforcement/pagination/batching/`fields_get`
parsing (`test_client.py`), every repository (`test_repositories.py`), capability
discovery orchestration (`test_discovery_capabilities.py`), catalogue field-mapping
classification (`test_discovery_catalogue_mapping.py`), and both CLI scripts —
including that a not-configured/blocked run never fabricates a result and never
leaks the configured secret (`test_verify_connection_script.py`), and that the
import planner correctly classifies `CREATE`/`MATCH_BY_*`/`BLOCKED` and never issues
a write call (`test_plan_import_script.py`).

## Opt-in live integration tests

`backend/tests/integration/test_odoo_integration.py` — marked
`@pytest.mark.odoo_integration` (registered in `backend/pyproject.toml`). **Disabled
by default** on two independent gates, both required:

1. `RUN_ODOO_INTEGRATION_TESTS=1` set in the environment.
2. `ODOO_BASE_URL`/`ODOO_DATABASE`/`ODOO_USERNAME` actually configured
   (`backend/.env`).

Without both, every test in this file is skipped with a message stating which gate
is missing — a plain `pytest` run is unaffected either way, so normal CI never
depends on a live Odoo instance.

To run for real, against a real Odoo instance (read-only — never modifies data):

```
cd backend
RUN_ODOO_INTEGRATION_TESTS=1 pytest -m odoo_integration -v
```

These tests check: server reachable + reports a version, authentication succeeds
with the configured credential, the four core catalogue models
(`product.template`/`product.product`/`product.category`/`res.company`) are
`AVAILABLE`, and a full `run_environment_verification()` pass does not come back
`BLOCKED` overall (individual optional/Enterprise-only checks may still be
`NOT_APPLICABLE` without that meaning the environment is unusable).

## Why no DB fixture is needed here

Unlike the Phase 3 catalogue tests (`backend/tests/integration/test_catalogue_*.py`),
nothing in `tests/unit/odoo/` or `tests/integration/test_odoo_integration.py` touches
PostgreSQL — the Odoo client and its tests are entirely independent of the
`db_session`/`db_engine` fixtures in `tests/conftest.py`.
