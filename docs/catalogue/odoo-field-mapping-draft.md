# Odoo Field Mapping (Draft)

**Draft only.** No Odoo instance, version, or edition has been inspected — per
[implementation-roadmap.md](../architecture/implementation-roadmap.md) open question #1,
this is still unresolved and blocks the actual Odoo client work (roadmap step 3). Every
mapping below is a best-effort guess based on Odoo's standard, widely-stable
`product.template`/`product.product` model and must be verified against the real target
instance before any import (roadmap step 5) is attempted. Flagged `[VERIFY]` throughout.

## Category → `product.category`

| Canonical field | Odoo target | Notes |
|---|---|---|
| `external_key` | `ir.model.data` external id (`module.terrific_bites`, `name=category_<slug>`) | Standard Odoo external-id pattern for idempotent import/re-import |
| `name_en` | `product.category.name` | `[VERIFY]` whether the target Odoo instance has multi-language (`name_ar` would need the `ar_001`/`ar_SA` locale activated and translated via `ir.translation`, or a custom field if translations aren't licensed/enabled) |
| `parent_external_key` | `product.category.parent_id` | Not used today (flat), but the field exists in Odoo if hierarchy is ever adopted |
| `code` | No standard Odoo field — `[VERIFY]` whether a custom field is needed, or whether the SKU prefix convention only needs to exist in our own PostgreSQL/import tooling and never touches Odoo at all |

## Product → `product.template` + `product.product`

| Canonical field | Odoo target | Notes |
|---|---|---|
| `external_key` | `ir.model.data` external id (`name=product_<slug>`) | Primary idempotency key for repeatable import/sync (rule 7) |
| `sku` | `product.product.default_code` (a.k.a. "Internal Reference") | `[VERIFY]` — Odoo's `default_code` lives on the **variant** (`product.product`), not the template; for our current single-variant-per-product reality this is a 1:1 mapping, but multi-variant products (if adopted) would need a `default_code` per variant |
| `name_en` | `product.template.name` | `[VERIFY]` multi-language, same caveat as category |
| `description_en` | `product.template.description_sale` ("Sales Description" — printed on quotes/orders) | `[VERIFY]` vs. `description` (internal notes field) — `description_sale` is the customer-facing one and the better fit |
| `category_external_key` | `product.template.categ_id` | |
| `sales_price` | `product.template.list_price` | `[VERIFY]` whether pricelists (`product.pricelist`) are used instead of/in addition to `list_price` in the target instance — affects [component-view.md](../architecture/component-view.md) §4's price-sync cadence design |
| `currency` | Company/pricelist currency setting, not a per-product field | `[VERIFY]` target instance's configured company currency is SAR |
| `tax_reference` | `product.template.taxes_id` (Sales taxes, many2many to `account.tax`) | Currently `null` for all products — needs a real tax mapping decision (see [catalogue-decisions-required.md](catalogue-decisions-required.md)) before import |
| `active` | `product.template.active` | |
| `sellable` | `product.template.sale_ok` | |
| `unit_of_measure` | `product.template.uom_id` / `uom_po_id` | Currently `null` for all products — `[VERIFY]` default UoM to use (likely "Units") |
| `primary_image` | `product.template.image_1920` (base64-encoded binary) | Odoo auto-derives smaller variants (`image_1024`/`image_512`/`image_128`); only the primary needs to be pushed |
| `additional_images` | `product.image` (Odoo 15+ "Extra Product Media") or a custom gallery module | `[VERIFY]` availability depends on Odoo version |
| `variants` (sizes/flavors) | `product.template.attribute_line_ids` → `product.template.attribute_value_ids`, generating `product.product` variants | Only relevant for `buttercream-cake` today under the "don't fabricate variant data" rule (see [product-model.md](product-model.md)); if category-default sizes/flavors are later promoted to real variants, this is where they'd land |

## Explicitly NOT mapped to Odoo (per data-ownership.md)

`is_new`, `is_bestseller`, `badge_*`, `display_order`, `homepage_sections`, `moments`,
`recipients`, `marketing_*`, `seo_*`, `*_image_override`, `storefront_visible` — all
PostgreSQL/Admin-owned, never written to or read from Odoo.

## Open questions blocking a real (non-draft) mapping

1. Odoo version/edition/hosting — Community vs. Enterprise changes model availability
   (e.g. Extra Product Media, multi-currency pricelists).
2. Whether Arabic is a first-class Odoo language on the target instance.
3. Confirm `default_code` uniqueness constraints/format expectations in the target
   instance before finalizing the `TB-<CODE>-<SEQ>` SKU convention.
4. Confirm tax configuration (single SAR VAT rate vs. per-category/product tax classes).
