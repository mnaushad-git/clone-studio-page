# Odoo Catalogue Field Mapping (Phase 4)

Supersedes the draft status of
[docs/catalogue/odoo-field-mapping-draft.md](../catalogue/odoo-field-mapping-draft.md)
with a *mechanism* for evidence-based classification — `app/integrations/odoo/discovery/catalogue_mapping.py`
— rather than a one-time hand-written guess. The actual classification results for a
given Odoo instance are produced by running `verify_odoo_connection --discover-fields`
against it; this document explains how to read that output, not a frozen table of
values (those live in the generated `data/odoo/odoo-environment-report.json`, which is
instance-specific and regenerated on every run).

## Classification enum

Every canonical field gets exactly one of:

| Classification | Meaning |
|---|---|
| `STANDARD_FIELD_CONFIRMED` | A standard Odoo field exists on this instance and was found by `fields_get`. |
| `STANDARD_FIELD_PARTIAL` | Expected to be a standard field, but not yet confirmed live (no discovery ran). |
| `CUSTOM_FIELD_EXISTS` | A non-standard field already present on this instance covers it. |
| `CUSTOM_FIELD_REQUIRED` | No standard or existing custom field covers it — would need a new Odoo field. Not recommended unless there's a genuine ownership/integration need (see below). |
| `POSTGRESQL_ONLY` | Not an Odoo concept at all — owned entirely by PostgreSQL/Admin merchandising data. |
| `DERIVED` | Computed from other fields (e.g. numeric ids alongside the external-key). |
| `NOT_SUPPORTED` | Checked against a live instance and the field/model is genuinely absent. |
| `REQUIRES_BUSINESS_DECISION` | Blocked on a business decision, not an Odoo fact (see `data/catalogue/catalogue-decisions.json`). |
| `REQUIRES_ODOO_CONFIGURATION` | Depends on Odoo-side setup (language activation, external-id creation) not yet done in this phase. |

Each row also carries an **evidence** level:

- `VERIFIED_FACT` — observed on a real `fields_get`/`search_read` call this run.
- `INFERRED_MAPPING` — a reasonable mapping (e.g. "currency comes from
  `res.company.currency_id`") that isn't a single `fields_get` lookup away from being
  verified as a fact, or needs Odoo-side configuration to be checked meaningfully.
- `UNVERIFIED_ASSUMPTION` — no live discovery ran at all; carried over from the draft
  mapping document only.

`app.integrations.odoo.discovery.catalogue_mapping.build_category_mapping()` and
`build_product_mapping()` take a `fields_by_model` dict (from
`discovery/fields.py::discover_fields_for_models()`, or `None` if discovery never
ran) and return the classified rows — see
`backend/tests/unit/odoo/test_discovery_catalogue_mapping.py` for the classification
rules exercised against both a populated and an empty/`None` input.

## Canonical fields covered

Category: `external_key`, `code`, `slug`, `name_en`, `name_ar`, `description_en`,
`description_ar`, parent category, `active`, display order.

Product: `external_key`, SKU, `slug`, `name_en`, `name_ar`, `description_en`,
`description_ar`, short description, category, product type, unit of measure,
`active`, sellable, base sales price, currency, tax mapping, primary image,
additional images, product template ID, product variant ID.

## PostgreSQL-only fields (never sent to or read from Odoo)

`code`, `slug` (both category and product), `description_en`/`description_ar` on
category, short description on product — plus everything already listed in
[data-ownership.md](../architecture/data-ownership.md) and
`odoo-field-mapping-draft.md`'s "Explicitly NOT mapped" section (`is_new`,
`is_bestseller`, `badge_*`, `display_order`, `homepage_sections`, `moments`,
`recipients`, `marketing_*`, `seo_*`, `*_image_override`, `storefront_visible`).

## No custom Odoo fields recommended

Per this phase's instruction not to recommend custom fields without a genuine
ownership/integration need: nothing in this phase's mapping recommends adding a
custom field to Odoo. Fields with no standard equivalent (`code`, `slug`, short
description) stay `POSTGRESQL_ONLY` rather than becoming `CUSTOM_FIELD_REQUIRED` —
there is no integration reason Odoo itself needs a URL slug or a 3-letter SKU-prefix
code.

## Live findings, 2026-07-28 (Phase 4B)

Running `verify_odoo_connection --discover-fields --check-authentication` against
`terrific_dev` (Odoo 19.0-20260720) produced `data/odoo/odoo-environment-report.json`'s
current `field_discovery`/`catalogue_mapping` sections — every category/product row
listed in the "Canonical fields covered" section above is now `VERIFIED_FACT`
evidence (not `UNVERIFIED_ASSUMPTION`), confirming `docs/catalogue/odoo-field-mapping-draft.md`'s
original guesses were correct: `name`→`name`, `description_sale` for the sales
description, `categ_id`, `type`, `uom_id`, `active`, `sale_ok`, `list_price`,
`taxes_id`, `image_1920` all exist exactly as assumed.

Two things the mechanical classifier doesn't know about, found by additional
read-only calls:

- **Arabic is installed and active** (`res.lang` search: `en_US` and `ar_001`, both
  `active=true`). This satisfies the language-activation prerequisite the
  `name_ar`/`description_ar` rows note (`REQUIRES_ODOO_CONFIGURATION` — still correct
  as the classification, since no Arabic *values* exist yet for any of the 26
  products, only the language itself is ready).
- **A custom Odoo module, `terrific_bites_custom` (v19.0.1.0.0), is already
  installed** and defines eight `x_*` fields on both `product.template` and
  `product.product`: `x_storage_instructions` (html), `x_ingredients` (html),
  `x_allergens` (html), `x_loyalty_points` (integer), `x_is_gift_card` (boolean),
  `x_allows_custom_inscription` (boolean), `x_inscription_color_ids` (many2many →
  `terrific.inscription.color`), `x_related_product_ids` (many2many →
  `product.template`, labelled "You May Also Like"). None of these were previously
  known to this repo's canonical catalogue schema (`data/catalogue/products.json` has
  no ingredients/allergens/storage-instructions/gift-card/inscription/loyalty fields
  at all) — every one of them should be reclassified from not-considered to
  **`CUSTOM_FIELD_EXISTS`** if/when this repo's canonical product schema is extended
  to cover them. This phase does not extend the schema (out of scope) — it only
  records that the fields already exist on the target instance, ready to be mapped
  whenever a business/architecture decision is made to use them. See
  [catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md) for the
  larger implication (this module also defines homepage-section/hero-slide/
  announcement models that materially overlap with the still-open `D16` decision).

## How to regenerate this against a real instance

```
cd backend
python -m app.scripts.verify_odoo_connection --discover-fields --check-authentication
```

Output lands in `data/odoo/odoo-environment-report.json` under `field_discovery` and
`catalogue_mapping`. Re-run any time the target instance's configuration changes
(language activation, a new module installed) — this document describes the
mechanism, the report is the current evidence.
