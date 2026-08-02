# Odoo Integration — Operations Runbook (Phase 4)

Practical steps for an operator (developer or the business) to configure and verify
Odoo connectivity. This phase never imports data — this runbook stops at
verification and planning.

## 1. Configure connection details

Copy `backend/.env.example` to `backend/.env` if you haven't already (never commit
`backend/.env` — it's gitignored), then set:

```
ODOO_BASE_URL=http://localhost:8069      # your instance's URL
ODOO_DATABASE=<your database name>
ODOO_USERNAME=<a login with read access to product/category/tax/uom/currency/pricelist/stock>
ODOO_PASSWORD=<password>                  # or ODOO_API_KEY — set exactly one
```

Optional: `ODOO_COMPANY_ID`, `ODOO_DEFAULT_PRICELIST_ID`, `ODOO_DEFAULT_WAREHOUSE_ID`
if the instance is multi-company/multi-pricelist and a specific one should be
targeted; `ODOO_TIMEOUT_SECONDS`, `ODOO_MAX_RETRIES`, `ODOO_RETRY_BACKOFF_SECONDS`,
`ODOO_READ_BATCH_SIZE` to tune transport behaviour (sane defaults exist for all of
these — see [environment-variables.md](../backend/environment-variables.md)).

## 2. Verify connectivity

```
cd backend
python -m app.scripts.verify_odoo_connection
```

Read the terminal summary first. If `overall_status` is `BLOCKED`:

| Blocker text contains | Likely cause | Fix |
|---|---|---|
| "is not configured" | One of `ODOO_BASE_URL`/`DATABASE`/`USERNAME` is empty | Fill in `backend/.env`, step 1 |
| "Invalid Odoo configuration" | Bad URL, non-positive timeout, both/neither password+API key set | Check the printed issue list, fix `.env` |
| "Odoo server is reachable" = `BLOCKED` | Wrong URL/port, instance not running, network/firewall | Confirm the instance is up and reachable from where this runs |
| "Authentication succeeds" = `BLOCKED` | Wrong database name, wrong username, wrong password/API key | Re-check credentials against the actual Odoo login screen |

If `overall_status` is `PARTIAL`, connectivity and auth are fine — read the
`blocking_check_ids` list for which specific model/field checks failed (e.g. a
model genuinely not installed on this edition) and treat those as informational
unless they're on the "required" list in
[odoo-environment-verification.md](odoo-environment-verification.md).

## 3. Review the field-mapping evidence

```
python -m app.scripts.verify_odoo_connection --discover-fields
```

Inspect `data/odoo/odoo-environment-report.json`'s `catalogue_mapping` section — see
[odoo-catalogue-field-mapping.md](../integrations/odoo-catalogue-field-mapping.md)
for how to read the classification/evidence columns.

## 4. Review the dry-run import plan

```
python -m app.scripts.plan_odoo_catalogue_import
```

Inspect `data/odoo/catalogue-import-plan.json`. `unresolved_required_configuration`
lists exactly which business/Odoo-config decisions (from
`data/catalogue/catalogue-decisions.json`) are still blocking a real import — resolve
those (business sign-off for category codes/SKUs/tax/product-type/opening inventory;
Odoo-side confirmation for the real tax record, UoM record, currency) before
considering Step 5 in
[catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md).

## 5. What comes after this phase (not performed here)

- Resolve the open decisions above with explicit business/Odoo-side sign-off.
- Re-run the planner; once every item is `CREATE`/`MATCH_*` with zero blocking
  issues, a future phase implements the actual write path (still isolated to
  `app/integrations/odoo/`, still going through a reviewed, tested adapter) to
  perform the import.
- Build the product-sync worker (Odoo → PostgreSQL) once real catalogue data exists
  in Odoo to sync from.

## Troubleshooting a live Odoo 19 Community instance

- Default local port is `8069` unless changed (`ODOO_BASE_URL=http://localhost:8069`).
- The database name is whatever you named it when you first created it (Odoo's
  database-manager screen, or `--database` at server startup) — it is *not*
  necessarily "odoo" or the instance's hostname.
- If login fails with a database name that "looks right", confirm case sensitivity
  and that multi-database mode isn't listing a different actual internal name.
- API keys (Settings → Users → a user → Account Security → API Keys) are the
  preferred credential over a real user password for integration use — set
  `ODOO_API_KEY` instead of `ODOO_PASSWORD` when one is available.
- Odoo 19 also exposes a newer `/json/2/<model>/<method>` API alongside `/jsonrpc` —
  see [odoo-client.md](odoo-client.md) §2a. It **requires an API key** (no
  password/database auth); if you provision one for JSON-2 evaluation purposes, treat
  it as a separate follow-up task, not a required step for this client, which stays
  on JSON-RPC.

## Known gaps on the `terrific_dev` local instance (as of 2026-07-28)

Not blockers for this phase (read-only verification only), but worth knowing before
attempting anything beyond it:

- **No Accounting/tax setup completed**: `l10n_sa`/`l10n_gcc_invoice` are installed,
  but the Fiscal Localization wizard hasn't been run — `account.tax` has zero records
  of any kind. `D08` needs a real tax record created (a write operation, out of scope
  here) before it can be more than a business decision on paper.
- **No Inventory/stock app installed**: `stock.quant`/`stock.warehouse` are
  unavailable, and `product.template.type` only offers `consu`/`service`/`combo` (no
  "Storable"). Installing the Inventory app is a prerequisite for `D19` regardless of
  which opening-inventory policy the business picks.
- **No `product.pricelist` records exist** — the instance has no default sales
  pricelist configured at all.
- **The instance is not empty**: 23 pre-existing `product.template` records exist
  (a mix of standard Odoo/eCommerce demo records — "Gift Card", "Top-up eWallet",
  "Standard delivery" — and an unrelated generic bakery placeholder catalogue —
  "Classic Red Velvet Cake", "Vanilla Bean Cupcake", etc.). None of their names, SKUs,
  or categories match any of the 26 canonical Terrific Bites products (confirmed both
  by `plan_odoo_catalogue_import`'s exact-match search and by manual review of all 23
  records) — so this is a **hygiene note, not a conflict** — see
  [catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md).
- **A custom module, `terrific_bites_custom`, is already installed** with its own
  models and product fields — a major finding, documented in
  [catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md).
