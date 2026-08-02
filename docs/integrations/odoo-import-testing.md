# Odoo Import Testing

Describes what's covered by automated tests for the Phase 5 importer, and the live
integration test policy.

## Unit tests (no DB, no Odoo — safe to run anywhere, always run in CI)

- **`tests/unit/test_approval_gate.py`** — schema validation (missing file, invalid
  JSON, missing required field, invalid status, duplicate decision_id, empty list),
  gate evaluation (unresolved/rejected/approved/non-blocking decisions, `APPROVED`
  with null `approved_value` still counts as unresolved), checksum stability/order
  independence, and assertions against the real committed approval file (six
  decisions present, D09 already approved, the gate is not yet satisfied).
- **`tests/unit/odoo/test_write_client.py`** — every `WRITE_ALLOWED_OPERATIONS` pair
  is permitted; every `EXPLICITLY_FORBIDDEN_METHODS` method is rejected regardless of
  model; ten additional non-allowlisted `(model, method)` pairs spanning stock/tax/
  UoM/pricelist/company/module/user/access/unlink/archive are each rejected; writes
  are refused in every non-`APPLY` mode; an `UPDATE` without `before_state` is
  rejected; the `execute_kw` call shape (7-tuple matching Odoo's real RPC signature)
  and `retryable=False` are asserted directly against the fake transport; no Odoo call
  happens at all when a gate fails before it (transport call count assertion).
- **`tests/unit/odoo/test_odoo_import_planning.py`** — category/product `CREATE`
  payload generation (including UoM/type values sourced from approved decisions);
  `BLOCKED` when a required decision isn't approved; `MATCH` via PostgreSQL-stored id
  (zero Odoo calls), external XML ID, and the "multiple name matches still block"
  case; SKU-match-requires-adoption for products; variant-skip planning (only
  buttercream-cake's non-default size, never the default-delta-zero size, never a
  simple product); environment fingerprint determinism (timestamp-independent,
  company-dependent).

Run: `pytest tests/unit -q` (170 tests total across the repo as of this phase, all
passing — see the completion report for the exact count including pre-existing tests).

## Integration tests (real PostgreSQL required, Odoo mocked)

- **`tests/integration/test_odoo_import_service.py`** — follows the same `db_session`
  fixture pattern as Phase 3's `test_catalogue_seed_service.py` (real Postgres,
  migrations applied, one rolled-back transaction per test). Odoo itself is always
  mocked here (`_connect()` monkeypatched to a `FakeTransport`-backed `OdooClient` — no
  live Odoo instance is ever required or contacted by this file). Covers: `--apply`
  refused without `--confirm-import` (no run row written); `--apply` refused against
  the real, currently-unresolved approval file; `--apply` refused when every plan item
  is `BLOCKED` and `--allow-partial` isn't set; `--dry-run` persists exactly one run
  row plus one item row per canonical category/product/variant-skip (33 for the real
  26-product/6-category catalogue) with zero Odoo writes; `--validate` reports (not
  raises) when Odoo is unreachable and never writes a run row.

Run: `pytest tests/integration/test_odoo_import_service.py -q` (requires
`DATABASE_URL` pointing at a real, migrated PostgreSQL — see
[../backend/local-development.md](../backend/local-development.md)).

**Not executed during this phase's implementation** — no local PostgreSQL was reachable
in the implementation environment (a Postgres server was present on the default port
but under different, non-project credentials; guessing credentials was not attempted).
These tests are written, pass `ruff`/`mypy`, and collect cleanly under `pytest
--collect-only`, but have not been run end-to-end against a live database. Run them
before the first `--apply` is ever attempted.

## Live Odoo integration tests (opt-in, read-only only in normal CI)

Following the existing `odoo_integration` pytest marker convention
(`docs/integrations/odoo-testing.md`, Phase 4): normal CI **never** performs Odoo
writes. Any live-write test (creating a test record, idempotent second import,
XML-ID recovery, image upload, gallery upload, reconciliation against a real
instance) must be explicitly opt-in and must run against a **confirmed non-production
test environment** — never the instance the current `data/odoo/odoo-environment-report.json`
was captured against unless that instance has been separately, explicitly confirmed
safe for catalogue creation. This phase does not add any live-write test to the
default suite; none should be added without that explicit confirmation.

## What's not yet covered by an automated test

Full end-to-end `--apply` against a real Odoo instance (categories → products →
variants → images → reconciliation) — inherently requires the live-write
confirmation above, which this phase does not have. The write-path logic itself
(`_apply_category_item`/`_apply_product_item`/`_apply_images` in
`odoo_import_service.py`) is exercised by `mypy` and by construction shares the exact
same matching/payload code the tested `--dry-run` path uses, but the literal Odoo
`create`/`write` calls inside an `--apply` run have not been exercised by any test in
this phase.
