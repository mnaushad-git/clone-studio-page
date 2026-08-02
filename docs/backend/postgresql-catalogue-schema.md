# PostgreSQL Catalogue Schema

Phase 3 (PostgreSQL Catalogue Foundation). Implements the relational model approved in
[docs/catalogue/final-data-ownership.md](../catalogue/final-data-ownership.md) and
[docs/catalogue/postgresql-field-mapping-draft.md](../catalogue/postgresql-field-mapping-draft.md),
via Alembic migration `0002_catalogue_foundation`
(`backend/app/db/alembic/versions/0002_catalogue_foundation.py`).

No Odoo client, no catalogue API, no frontend integration — see
[CLAUDE.md](../../CLAUDE.md) Phase 3 scope boundaries. This document describes the
schema as implemented, not the target architecture in general (see
[data-ownership.md](../architecture/data-ownership.md) for that).

## Conventions

- Every table uses a `UUID` primary key generated application-side (Python `uuid4()`),
  except two pure join tables (`catalogue_product_moments`,
  `catalogue_product_recipients`) which use a composite primary key of their two
  foreign keys — there is no surrogate id where the pair itself is already the natural
  key.
- Odoo identifiers (`odoo_category_id`, `odoo_product_template_id`,
  `odoo_product_variant_id`, `odoo_pricelist_id`) are plain nullable `Integer` columns.
  **They are never used as PostgreSQL primary keys.**
- `created_at`/`updated_at` are `TIMESTAMP WITH TIME ZONE`, defaulted and
  auto-updated by the database (`server_default=now()`, `onupdate=now()`).
- Odoo-syncable entities (categories, products, variants, prices, availability,
  images) carry `source_system`, `source_updated_at`, `last_synced_at` — provenance
  columns with no sync job writing to them yet (Phase 3 seeds `source_system='seed'`
  only).
- Stable business identifiers (`external_key`, `sku`, `slug`, category `code`) are
  unique-constrained and are the join key used by the seed service, since no Odoo IDs
  exist yet.

## Entity relationship summary

```
catalogue_categories (self-referencing parent_id)
        │ 1:N
catalogue_products (FK category_id)
   │ 1:N                                   │ 1:N
catalogue_product_variants          catalogue_product_images (nullable FK variant_id)
   │ 1:N        │ 0:1                      │
   │            └── catalogue_product_availability (unique per variant)
   └── catalogue_product_prices (unique active row per variant+currency)

catalogue_products ── 1:1 ── catalogue_product_merchandising
                              (nullable FKs → catalogue_product_images, for
                               storefront/mobile image overrides)

storefront_sections ── 1:N ── storefront_section_products (FK product_id)

catalogue_moments ──N:N── catalogue_product_moments ──N:N── catalogue_products
catalogue_recipients ──N:N── catalogue_product_recipients ──N:N── catalogue_products

catalogue_product_recommendations (FK product_id, recommended_product_id →
                                    catalogue_products; self-recommend forbidden)

integration_sync_checkpoints (standalone; unique per integration_name+entity_type)
catalogue_seed_runs (standalone; append-only audit log, no updated_at)
```

## Tables

### `catalogue_categories`
Odoo-owned identity (`external_key`, `code`, `name_en`/`ar`) plus Admin-owned
presentation (`display_order`, `active`) — see
[data-ownership.md](../architecture/data-ownership.md) §4 for why these live in one
table rather than split like products/merchandising: category presentation ownership
is genuinely simpler than product merchandising and doesn't yet need a separate table.

Unique: `external_key`, `code`, `slug`. Self-referencing `parent_id` (nullable,
`CHECK (parent_id IS NULL OR parent_id != id)` prevents direct self-parenting).
Indexes: `active`, `parent_id`, `odoo_category_id`.

### `catalogue_products`
Odoo-owned commercial identity. **Never stores a price directly** — price lives on
`catalogue_product_prices`, keyed by variant, since even "simple" products get exactly
one default variant (see [catalogue-seeding.md](catalogue-seeding.md)).

Unique: `external_key`, `sku`, `slug`. Required FK: `category_id`.
`CHECK (product_type IN ('simple', 'variant_parent'))`,
`CHECK (source_system IN ('seed', 'odoo', 'admin'))`.
Indexes: `category_id`, `active`, `sellable`, `odoo_product_template_id`, `name_en`.

### `catalogue_product_variants`
One row per sellable unit. `is_default` marks the variant used when a product has no
meaningful variation; a partial unique index
(`uq_catalogue_product_variants_one_default_per_product`, `WHERE is_default`)
enforces **at most one default variant per product** at the database level.
Per-axis attribute data (size, flavor, or any other ops/Odoo-defined axis) lives in the
related `catalogue_product_attribute_values` table (one row per variant per axis), not
as a JSONB column on this table — see
[odoo-catalogue-variant-model.md](../integrations/odoo-catalogue-variant-model.md).

### `catalogue_product_prices`
`price_includes_tax` is **nullable and always seeded as `NULL`** — the storefront has
an unresolved VAT-inclusive-vs-exclusive contradiction (decision D21 in
[catalogue-decisions.json](../../data/catalogue/catalogue-decisions.json)); this schema
preserves that ambiguity rather than picking a side. A partial unique index
(`uq_catalogue_product_prices_one_active_per_variant_currency`, `WHERE active`)
enforces **at most one active price per (variant, currency)**.
`CHECK (amount >= 0)`, `CHECK (valid_to IS NULL OR valid_to >= valid_from)`.

### `catalogue_product_availability`
`quantity_available` is nullable and **never seeded** with a fabricated value — no
opening-inventory decision has been made (D19). `availability_status` is constrained to
`UNKNOWN | AVAILABLE | OUT_OF_STOCK | DISCONTINUED | PREORDER`. Unique per
`product_variant_id` (one current row, no history table this phase).

### `catalogue_product_images`
`product_id` required, `product_variant_id` nullable. `original_path` preserves the
current repo-relative source path as provenance; `storage_url` stays `NULL` until a
media migration to object storage happens. `CHECK (image_role IN ('PRIMARY',
'GALLERY', 'STOREFRONT_OVERRIDE', 'MOBILE_OVERRIDE'))`.

### `catalogue_product_merchandising`
Admin-Portal-owned, never touched by an Odoo sync. Exactly one row per product
(`UNIQUE (product_id)`). `is_bestseller` is nullable and never inferred — the concept
has no computed definition yet.

### `storefront_sections` / `storefront_section_products`
Modeled to support future homepage-rail wiring but **seeded with zero rows this
phase** — see [catalogue-seeding.md](catalogue-seeding.md) for why. Unique
`(section_id, product_id)` prevents a duplicate assignment.

### `catalogue_moments` / `catalogue_recipients`
Pure PostgreSQL/Admin vocabulary tables, independent of the Odoo category hierarchy.
Both require a unique `code`; the canonical JSON doesn't provide one, so the seed
service derives it mechanically from `slug` (see
[catalogue-seeding.md](catalogue-seeding.md)).

### `catalogue_product_moments` / `catalogue_product_recipients`
Composite-PK join tables (`(product_id, moment_id)` / `(product_id, recipient_id)`) —
no surrogate id.

### `catalogue_product_recommendations`
`CHECK (product_id != recommended_product_id)` — a product can never recommend
itself, enforced by the database, not just application logic.
`recommendation_type IN ('MANUAL', 'SAME_CATEGORY', 'FREQUENTLY_BOUGHT')`. Seeded with
**zero rows** this phase — the canonical source file ships empty by design (D14); no
recommendation is synthesized.

### `integration_sync_checkpoints`
Unique `(integration_name, entity_type)`. Exists for a future sync worker; nothing
reads or writes it yet.

### `catalogue_seed_runs`
Append-only audit log (no `updated_at`) of every seed attempt — dry-run, success, or
failure — including counts and an error summary. See
[catalogue-seeding.md](catalogue-seeding.md).

## What's deliberately absent

Per [CLAUDE.md](../../CLAUDE.md) scope rules: no Odoo client/tables, no cart/order/
customer/payment tables, no review/rating tables, no product API. `tax_reference` and
`unit_of_measure` remain unresolved placeholders (D08/D09) — populated with whatever
value the canonical JSON carries (`NULL` for every product today), never guessed.
