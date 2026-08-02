# Odoo Catalogue Import — Operations Runbook

Step-by-step sequence for operating the Phase 5 importer safely. See
[odoo-catalogue-import.md](odoo-catalogue-import.md) for the architecture and
[odoo-operations-runbook.md](odoo-operations-runbook.md) for base Odoo connectivity
troubleshooting (env vars, common connection errors) carried over from Phase 4.

## 0. Prerequisites

- `backend/.env` has `ODOO_*` configured and verified (Phase 4 —
  `python -m app.scripts.verify_odoo_connection` returns `VERIFIED` or an acceptable
  `PARTIAL`).
- PostgreSQL is reachable and migrated to at least revision `0003`
  (`alembic upgrade head`, from `backend/`).
- You have reviewed [odoo-import-approval-gate.md](odoo-import-approval-gate.md) and
  understand which decisions are still open.

## 1. Check the approval gate

```
python -m app.scripts.check_catalogue_import_approvals
```

If this exits non-zero, `--apply` will refuse to run — this is expected and correct
until every blocking decision in
`data/catalogue/catalogue-business-approvals.json` is `APPROVED` with a real
`approved_value`. Do not proceed past this step by editing code to bypass it; edit the
approval file (with real business sign-off) instead.

## 2. Validate

```
python -m app.scripts.import_odoo_catalogue --validate
```

Confirms: canonical catalogue loads, approval file parses, Odoo is reachable and
authenticated, company currency is SAR. Fix anything reported here before continuing.

## 3. Plan

```
python -m app.scripts.import_odoo_catalogue --plan
```

Writes `data/odoo/catalogue-import-execution-plan.json`. Review `action_counts` and
`blocking_item_count`. Every category/product should resolve to `CREATE`, `MATCH`, or
(if approvals are still open) `BLOCKED` — never silently skipped.

## 4. Dry run

```
python -m app.scripts.import_odoo_catalogue --dry-run
```

Writes `data/odoo/catalogue-import-dry-run-report.json` and persists a real
`odoo_catalogue_import_runs`/`odoo_catalogue_import_items` audit trail in PostgreSQL —
**with zero Odoo writes**. Inspect the report:

- Confirm `blocking_item_count` matches what you expect (ideally `0` before a full
  production import).
- Confirm the expected create/update/skip counts (first run against a clean
  environment: ~6 category creates, ~26 product-template creates, ~29 image imports,
  plus XML-ID creates for each).
- Confirm no secrets appear anywhere in the file (`grep -i` for `password`, `api_key`,
  `session`, `cookie` — should find nothing).

## 5. Human review gate

**Stop here.** Do not run `--apply` without:

1. The approval file being complete (step 1 passing).
2. Explicit confirmation the target Odoo environment is safe for catalogue creation
   (not a shared production instance being used for something else, or if it is,
   explicit sign-off that catalogue creation there is intended).
3. The dry-run report having been reviewed by a human, not just a script exit code.
4. The exact expected create/update counts from step 4 being explicitly accepted.

This mirrors CLAUDE.md Phase 5 §17 exactly — this project's convention requires all
four before `--apply` is run, on top of (not instead of) the approval gate.

## 6. Apply (once every gate above is genuinely satisfied)

```
python -m app.scripts.import_odoo_catalogue --apply --confirm-import
```

`--allow-partial` is available if only some items should import while others remain
blocked — **do not use it for the initial production import** without explicit,
separate sign-off (CLAUDE.md Phase 5 §11). Without it, any blocked item refuses the
entire run before a single Odoo write happens.

## 7. Reconcile

```
python -m app.scripts.import_odoo_catalogue --reconcile
```

Writes `data/odoo/catalogue-import-reconciliation-report.json`. Confirm `"clean":
true`. If not, investigate `field_mismatches`/`postgresql_mapping_mismatches` before
trusting the import.

## If something needs to be undone

```
python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id <the apply run's id>
```

See [odoo-import-rollback.md](odoo-import-rollback.md) — produces a plan only; every
actual archive/restore/delete is executed manually by a human in Odoo.

## What this runbook does not cover

Recurring/scheduled synchronisation (not implemented this phase — CLAUDE.md Phase 5
§10 explicitly excludes it), catalogue FastAPI endpoints, Storefront/Admin Portal
connection, cart/checkout/orders/payments. See
[../catalogue/catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md)
for the full readiness picture and recommended next phase.
