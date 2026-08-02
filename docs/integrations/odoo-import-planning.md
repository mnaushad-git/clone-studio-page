# Odoo Catalogue Import Planning (Dry-Run)

`python -m app.scripts.plan_odoo_catalogue_import` produces a per-category,
per-product planned action **without ever creating, updating, archiving, or deleting
anything in Odoo** — every Odoo call it makes is a `search_read` via
`app/integrations/odoo/repositories/{categories,products}.py`, which only ever call
`OdooClient`'s read-only surface (see
[odoo-read-only-safety.md](odoo-read-only-safety.md)).

## Usage

```
cd backend
python -m app.scripts.plan_odoo_catalogue_import
python -m app.scripts.plan_odoo_catalogue_import --output <path> --json
```

Exit code `0` only if every item resolves with no blocking issues; `1` if any item is
`BLOCKED` (Odoo unreachable, an open business/Odoo-config decision, or a genuine
name/SKU conflict).

## What it reads

- `data/catalogue/categories.json`, `data/catalogue/products.json` — the canonical
  Phase 2A seed data (26 products, 6 categories).
- `data/catalogue/catalogue-decisions.json` — filters to decisions that
  `blocks_odoo_import: true` and are not yet `"status": "APPROVED"` (currently D03,
  D04, D08, D09, D10, D19 — category codes, SKUs, tax mapping, UoM, product-type
  classification, opening inventory).
- A fresh Odoo connection (built from current `backend/.env` settings, independent of
  any previously-generated `odoo-environment-report.json`) — used to search for
  conflicts live, not from a stale cache.

## Action classification

For each category/product, in this priority order:

1. **`MATCH_BY_EXTERNAL_KEY`** — an `ir.model.data` row already exists under the
   `terrific_bites` module namespace for this slug (see
   [odoo-external-key-strategy.md](odoo-external-key-strategy.md)). Only possible if
   a prior import already ran.
2. **`MATCH_BY_SKU`** (products only) — an existing `product.template` has the same
   `default_code`.
3. **`MATCH_BY_NAME_REVIEW_REQUIRED`** — an existing `product.category`/
   `product.template` has the exact same name, with no external-key or SKU match —
   flagged for human review since a name match alone doesn't prove it's the same
   record.
4. **`BLOCKED`** — either Odoo couldn't be reached/authenticated at all, or a relevant
   open decision (from `catalogue-decisions.json`) blocks import for this category/
   product.
5. **`CREATE`** — no conflict found, and no relevant decision remains open. This is
   the only outcome that would eventually (in a future, write-capable phase) create a
   new record.

`SKIP` is reserved for a future refinement (e.g. explicitly excluding a product from
import) — not produced by the current classification logic, since every one of the 26
products/6 categories is currently in scope.

## Report shape

Written to `data/odoo/catalogue-import-plan.json`:

```json
{
  "generated_at": "...",
  "odoo_connection": "ok | unavailable: <reason>",
  "unresolved_required_configuration": [{"decision_id": "D03", "title": "...", "status": "..."}],
  "action_counts": {"CREATE": 0, "BLOCKED": 32},
  "blocking_item_count": 32,
  "field_mappings": {"category": [...], "product": [...]},
  "categories": [{
    "entity_type": "category", "external_key": "...", "identifier": "CUP",
    "canonical_name": "Cupcakes", "proposed_odoo_model": "product.category",
    "existing_match": null, "match_strategy": null, "proposed_action": "BLOCKED",
    "blocking_issues": ["..."], "warnings": [], "mapped_fields": {...},
    "omitted_postgresql_only_fields": ["code", "slug", "..."],
    "confirmation_status": {"code": "BUSINESS_CONFIRMATION_REQUIRED"}
  }],
  "products": [ /* same shape, product_ keys */ ]
}
```

## Current real result

As of Phase 2B, D03/D04/D08/D09/D10/D19 were all open (see
`data/catalogue/catalogue-decisions.json`), so **every** category and product planned
to `BLOCKED` regardless of Odoo reachability — this was the correct, honest state of
readiness, not a bug: see
[catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md) for why
Odoo import specifically (unlike PostgreSQL schema work) has genuine open blockers.

**Phase 4B update (2026-07-28):** a real Odoo connection is now configured
(`backend/.env` → `terrific_dev`), and `D09` (unit of measure) is now `APPROVED` on
live evidence (`uom.uom` id=1, name `"Units"`) — see
[odoo-configuration-checklist.md](../catalogue/odoo-configuration-checklist.md).
Re-running the planner against the live instance drops `unresolved_required_configuration`
from 6 decisions to 5 (`D03`, `D04`, `D08`, `D10`, `D19`) and every per-item
`blocking_issues` list now cites the specific still-open decision(s) rather than
"cannot verify against Odoo" (connectivity is fine — `"odoo_connection": "ok"` in
`data/odoo/catalogue-import-plan.json`). `action_counts` is still `{"BLOCKED": 32}` —
resolving one of six blocking decisions doesn't clear any item, since every category
still needs `D03` and every product still needs at least one of `D04`/`D08`/`D10`.
Live conflict detection (26 products + 6 categories, `ir.model.data`/SKU/name search
against the real instance) found zero conflicts of any kind — see
[catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md) for the
one caveat (23 unrelated pre-existing products on the instance, none of which match).
