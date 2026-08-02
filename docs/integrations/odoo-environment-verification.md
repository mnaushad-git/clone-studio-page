# Odoo Environment Verification

`python -m app.scripts.verify_odoo_connection` runs the phase's environment-
verification checklist against whatever `ODOO_*` settings are configured in
`backend/.env`, and writes a machine-readable report. Every call it makes is
read-only — see [odoo-read-only-safety.md](odoo-read-only-safety.md).

## Usage

```
cd backend
python -m app.scripts.verify_odoo_connection                       # runs everything
python -m app.scripts.verify_odoo_connection --check-connection
python -m app.scripts.verify_odoo_connection --check-authentication
python -m app.scripts.verify_odoo_connection --discover-capabilities
python -m app.scripts.verify_odoo_connection --discover-fields
python -m app.scripts.verify_odoo_connection --check-catalogue-conflicts
python -m app.scripts.verify_odoo_connection --output <path> --json
```

With no flags, it runs the full sequence: connection → authentication → capability
checklist → field discovery → catalogue conflict check (the last two only if
authentication succeeded).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Fully verified — reachable, authenticated, no blocked checks. |
| `1` | Ran, but at least one check is `BLOCKED` (missing model/field/access, etc.). |
| `2` | Could not run at all — Odoo not configured, or configuration invalid. |

## What it checks

`app/integrations/odoo/discovery/capabilities.py::run_environment_verification()`
produces one `CapabilityCheck` per item, each with a status:

- **`VERIFIED`** — a live fact observed on this run, backed by a real Odoo response.
- **`BLOCKED`** — attempted and failed (unreachable, denied, missing).
- **`UNVERIFIED`** — never attempted, because an earlier prerequisite (reachability,
  authentication) already failed.
- **`NOT_APPLICABLE`** — an optional check (e.g. the Enterprise-only image-gallery
  model) that doesn't gate overall readiness.

Checks cover: server reachability + version, authentication, selected company +
company currency, multi-company/multi-currency applicability, availability of every
required catalogue model (`product.template`, `product.product`, `product.category`,
`account.tax`, `uom.uom`, `res.currency`, `product.pricelist`, `stock.quant`, plus the
informational `stock.warehouse`/`product.image`), specific field presence
(`image_1920`, `barcode`, `description_sale`, `default_code` on both template and
variant, `sale_ok`, `active`, `type`, `attribute_line_ids`), supported `type` selection
values, and whether an existing Terrific Bites category already exists in the target
instance.

Every check runs independently — one failure (e.g. a missing model) never aborts the
rest, so the report always reflects the full picture reachable from wherever
verification actually got to.

## Report shape

Written to `data/odoo/odoo-environment-report.json` by default (`--output` to
override). Never contains a password, API key, session id, or cookie — see
`backend/tests/unit/odoo/test_verify_connection_script.py::test_report_never_contains_the_configured_secret`.

```json
{
  "generated_at": "...",
  "protocol": "jsonrpc",
  "base_url": "...",
  "database": "...",
  "overall_status": "VERIFIED | PARTIAL | BLOCKED",
  "server_version": {"server_version": "...", "server_serie": "...", "protocol_version": 1},
  "authenticated": true,
  "authenticated_uid": 2,
  "checks": [{"check_id": "...", "description": "...", "status": "...", "detail": "...", "evidence": {}}],
  "blocking_check_ids": ["..."],
  "field_discovery": {"product.template": {"name": "char", "...": "..."}},
  "catalogue_mapping": {"category": [...], "product": [...]},
  "catalogue_conflicts": {"categories": [...], "products": [...]}
}
```

## If Odoo is not configured or unreachable

The command still runs to completion and writes a report — it never fabricates a
result. `overall_status` is `"BLOCKED"`, and `blocker_reason` states exactly what's
missing (e.g. `ODOO_BASE_URL`/`ODOO_DATABASE`/`ODOO_USERNAME` all empty) or what
failed (connection refused, authentication rejected). This is the actual current
state of this repository — see [odoo-operations-runbook.md](odoo-operations-runbook.md)
for what to do next.

## Live run, 2026-07-28 (Phase 4B)

`backend/.env` now points at a real, reachable Odoo 19 instance
(`terrific_dev` @ `http://localhost:8069`, self-hosted/on-premise — the debug
traceback of an unrelated probe request revealed the server path
`C:\Program Files\Odoo 19.0.20260720\server\...`, which is on-premise Windows
install evidence, not Odoo.sh/Odoo Online). Running the full command produced:

- `overall_status`: **`PARTIAL`** — reachable, authenticated (`uid=2`), but one
  required check is `BLOCKED`.
- `server_version`: `19.0-20260720` (Community edition — confirmed via
  `ir.module.module`: `web_enterprise` is **not** among the 104 installed modules).
- `blocking_check_ids`: `["model_stock.quant"]` — the Inventory/stock app is not
  installed on this instance at all (`stock.quant`/`stock.warehouse` both report
  "Model not installed"; `stock` is absent from the installed-modules list). This is
  a real environment gap, not a client bug — see `catalogue-import-plan.json`'s D19
  entry.
- `company_currency`: company id 1 ("My Company", country Saudi Arabia), currency
  SAR (id 151) — confirms `D07`.
- `multi_company`: single company, single currency — no multi-company handling
  needed for this instance.
- Every other catalogue-relevant model (`product.template`, `product.product`,
  `product.category`, `account.tax`, `uom.uom`, `res.currency`, `product.pricelist`,
  `product.image`) is `VERIFIED`/available, including the Odoo-15+ multi-image
  gallery model.

The full report is at `data/odoo/odoo-environment-report.json`, regenerated by this
run (never contains a password/API key/session id — confirmed by
`test_report_never_contains_the_configured_secret`).

### Beyond the standard checklist

A few items in the Phase 4B verification brief aren't covered by
`run_environment_verification()`'s fixed checklist and were confirmed with
additional one-off, read-only calls through the same `OdooClient` (not persisted as
new automated checks in this phase — see
[odoo-catalogue-field-mapping.md](odoo-catalogue-field-mapping.md) and
[odoo-external-key-strategy.md](odoo-external-key-strategy.md) for where the results
are recorded):

- `ir.model`, `ir.model.fields`, `ir.model.data` are all readable (`read`/
  `fields_get` both succeed; record counts 523 / 10,609 / 25,504 respectively).
- Languages installed: `en_US` and `ar_001` (Arabic) — both active. The current
  integration user's own `lang` is `en_US`, `tz` is `Asia/Riyadh`.
- **A custom module, `terrific_bites_custom` (v19.0.1.0.0, author "Terrific Bites"),
  is already installed** on this instance — see
  [catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md)'s new
  "Critical Phase 4B finding" section for what it defines and why it matters.
