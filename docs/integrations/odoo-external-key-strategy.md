# Odoo External-Key Strategy

Resolves checklist item 13 ("how should the permanent external_key be persisted")
with an evidence-based recommendation, without creating anything in Odoo this phase.

## Options evaluated

| Option | Verdict |
|---|---|
| **`ir.model.data` external XML ID** (`terrific_bites.category_<slug>` / `terrific_bites.product_<slug>`) | **Recommended.** Standard, built into every Odoo install, no custom field, idempotent by construction (Odoo's own import tooling is built around it). |
| A pre-existing custom external-reference field | Rejected for this catalogue — no such field is known to exist on a stock `product.template`/`product.category`, and adding one would be a custom field with no integration need beyond what `ir.model.data` already provides. |
| SKU + PostgreSQL mapping only (no Odoo-side identifier at all) | Workable as a fallback, but weaker: SKU is a business value that *could* change (D04 is still open), whereas an external ID is a pure technical identifier never exposed to a user. Also gives no recovery path if the PostgreSQL mapping table itself is lost (see below). |
| Another supported mechanism | None identified with a comparable idempotency guarantee. |

## Recommendation by use case

- **Initial import**: create one `ir.model.data` row per category/product at import
  time, `module="terrific_bites"`, `name=<slug-derived>` exactly as already specified
  in [identifier-mapping-register.md](../catalogue/identifier-mapping-register.md)
  (D20) — e.g. `terrific_bites.category_cupcakes`, `terrific_bites.product_swiss-frosting`.
  This phase does **not** create these rows; `plan_odoo_catalogue_import.py` only
  *checks* for their prior existence (see below).
- **Ongoing synchronisation**: the product-sync worker (future phase) should upsert
  by external ID first, falling back to SKU match only when no external ID row exists
  yet (covers records created before the sync worker existed). This mirrors
  `plan_odoo_catalogue_import.py`'s own match-priority order:
  `MATCH_BY_EXTERNAL_KEY` → `MATCH_BY_SKU` → `MATCH_BY_NAME_REVIEW_REQUIRED` → `CREATE`.
- **Record recovery if PostgreSQL mappings are lost**: the external ID is the recovery
  path — `ir.model.data` lives inside Odoo itself, so even a total loss of the
  PostgreSQL `catalogue_categories`/`catalogue_products` tables (or their
  `odoo_category_id`/Odoo numeric-id columns) can be re-derived by re-querying
  `ir.model.data` for `module="terrific_bites"` and reading back `res_id`. This is
  precisely why rule 23 ("preserve Odoo numeric IDs separately from stable external
  keys") matters: the numeric `id` is Odoo's own primary key and is *not* guaranteed
  stable across a reimport into a different instance, but the external ID's `name`
  is chosen by us and stays stable.

## What this phase actually does

`app/scripts/plan_odoo_catalogue_import.py`'s `_external_key_match()` helper searches
`ir.model.data` (`module="terrific_bites"`, `name=<xml_id>`, `model=<odoo model>`) —
read-only — before falling back to SKU/name matching. On a fresh Odoo instance with no
prior import, this will find nothing (a `MATCH_BY_EXTERNAL_KEY` outcome only appears
if a prior, out-of-band import already created these rows). No xml_id is created in
this phase, per the explicit "do not create XML IDs or custom fields in this phase"
instruction.

## Live verification, 2026-07-28 (Phase 4B)

Confirmed directly against `terrific_dev` (Odoo 19.0-20260720), read-only:

- `ir.model.data` is readable (`check_access_rights('ir.model.data', 'read')` →
  `True`) and `fields_get` succeeds (13 fields). 25,504 `ir.model.data` rows exist on
  the instance in total (standard Odoo/module bootstrap data).
- **Zero** of those rows belong to `module="terrific_bites"`
  (`search_count([['module', '=', 'terrific_bites']])` → `0`).
- A direct spot-check search for the exact proposed xml_id names (`category_cupcakes`,
  `category_cakes`, `category_chocolates`, `category_donuts`, `category_gifts`,
  `category_extras`, `product_swiss-frosting`, `product_buttercream-cake`) under
  `module="terrific_bites"` returned zero matches.
- `plan_odoo_catalogue_import`'s own conflict check (run against all 6 categories and
  26 products, not just the spot-check sample above) independently confirms the same
  thing: every `existing_match` is `null`.

**Conclusion: the `terrific_bites.category_<slug>` / `terrific_bites.product_<slug>`
external-id namespace is confirmed technically valid and conflict-free** on this
instance — nothing needs to change about the strategy above. (Note: a *different*
module, `terrific_bites_custom`, is already installed and owns its own, unrelated
`ir.model.data` rows — e.g. `field_product_product__x_allergens` — under
`module="terrific_bites_custom"`, not `module="terrific_bites"`. The two module
namespaces don't collide, but see
[catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md) for why
that module's existence is still a significant finding for this integration.)
