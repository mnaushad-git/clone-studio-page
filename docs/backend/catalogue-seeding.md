# Catalogue Seeding

`CatalogueSeedService` (`backend/app/services/catalogue/seed_service.py`) loads the six
canonical JSON files under `data/catalogue/` and upserts them into PostgreSQL. Run via:

```bash
cd backend
python -m app.scripts.seed_catalogue --dry-run   # validates + computes changes, writes nothing
python -m app.scripts.seed_catalogue --apply      # writes
```

Both modes always insert one row into `catalogue_seed_runs` (status `DRY_RUN`,
`SUCCESS`, or `FAILED`) — even a dry-run's *attempt* is audited, only the catalogue
data itself is rolled back.

## How idempotency actually works

`run()` opens one `session.begin_nested()` (a SQL `SAVEPOINT`) around the whole load.
Every entity is upserted by its stable key (`external_key`, `sku`, or a composite
natural key for join tables — see [catalogue-repositories.md](catalogue-repositories.md)),
comparing each candidate field against the existing row and only writing if something
actually differs. At the end:

- **Dry-run or validation/write failure** → the savepoint is rolled back. Nothing from
  this run persists except the `catalogue_seed_runs` audit row (added *after* the
  savepoint is resolved, so it survives regardless of outcome).
- **Apply, success** → the savepoint is committed. The caller (`seed_catalogue.py`)
  still has to call `session.commit()` on the outer session/transaction itself.

### A real idempotency bug found while building this

The first version of every repository's `upsert_*` method returned a 2-tuple
`(row, bool)`, where the bool meant "just created" in the not-found branch but "value
changed" in the found branch. Because both cases can be `True`, the seed service
mislabeled *every changed-but-pre-existing row* as newly created on re-runs. It was
caught by actually running the seed twice against a real database and checking the
second run reported `skipped=229, created=0, updated=0` — not by a single-run
assertion, which would have looked correct. Fixed by making every upsert method return
a 3-tuple `(row, created, changed)` — see
[catalogue-repositories.md](catalogue-repositories.md). A second, related bug
(`NUMERIC` vs Python `float` comparison — e.g. `Decimal("7.99") != 7.99` for some
values, due to binary float representation) made price rows look "changed" on every
re-run even after the tuple fix; fixed by converting canonical prices through
`Decimal(str(x))` before comparison/storage, in `seed_service.py`.

## Two scope decisions made during seeding (not spelled out elsewhere)

1. **Variants.** Every `product_type == "simple"` product gets exactly one default
   `catalogue_product_variants` row. `product_type == "variant_parent"` products (26
   as of the "real variant pricing" and "generic N-attribute pipeline" rollouts —
   `buttercream-cake` plus 25 more, one per non-cake category) get the full Cartesian
   product of their `variants.attributes[]` axis values, each combination's delta
   composing additively into that combination's price. Per-axis identity (attribute
   code/name/value label) is written to `catalogue_product_attribute_values` — see
   [odoo-catalogue-variant-model.md](../integrations/odoo-catalogue-variant-model.md) —
   not a JSONB column (D11's original single-JSONB-list approach was superseded once
   flavor started carrying its own price effect and needed the same combinatorial
   treatment as size).

2. **Storefront sections.** `product-merchandising.json`'s `homepage_sections` field is
   a list of bare string labels (`"homepage_products_rail"`, etc.), not a canonical
   section catalog with real `title_en`/`description_en` content — no
   `data/catalogue/*.json` file defines one. Fabricating that content would violate the
   same "don't invent data" rule that governs the Arabic-content gaps. **Zero**
   `storefront_sections`/`storefront_section_products` rows are seeded this phase;
   populating them once real section content exists is an open item (see the Phase 3
   completion report).

## What is never seeded, by design

- `catalogue_product_availability` — **zero rows**. No real inventory concept exists in
  the source data (D19); fabricating a quantity would be worse than having none.
- `catalogue_product_recommendations` — **zero rows**. The source file ships empty by
  design (D14); only explicit canonical recommendations are ever seeded, never derived.
- `price_includes_tax` — always `NULL`. The VAT-inclusive-vs-exclusive question is a
  genuine, unresolved business contradiction (D21); the schema and the seed both refuse
  to guess.
- Arabic name/description fields — preserved as `NULL` wherever the source JSON has
  `null` (26/26 products, 6/6 categories today). Never auto-translated or fabricated.
- `code` on moments/recipients — the canonical JSON has no `code` field for these two
  entities (unlike categories, which do). The seed service derives one mechanically
  from `slug` (`"for-him"` → `"FOR_HIM"`) — deterministic and idempotent, but a real
  business-assigned code convention (like categories eventually got, D03) is an open
  item if one is ever needed.

## Expected counts (current canonical data — 26 products, 6 categories)

| Entity | Count |
|---|---|
| `catalogue_categories` | 6 |
| `catalogue_products` | 26 |
| `catalogue_product_variants` | 27 (25 simple + 2 for buttercream-cake) |
| `catalogue_product_prices` | 27 |
| `catalogue_product_images` | 29 |
| `catalogue_product_merchandising` | 26 |
| `catalogue_moments` | 6 |
| `catalogue_recipients` | 4 |
| `catalogue_product_moments` | 40 |
| `catalogue_product_recipients` | 38 |
| `catalogue_product_availability` | 0 |
| `catalogue_product_recommendations` | 0 |
| `storefront_sections` / `storefront_section_products` | 0 / 0 |

Verified by actually running `--dry-run`, `--apply`, and `--apply` again against a real
local PostgreSQL 16 instance — see the Phase 3 completion report for the literal command
output.
