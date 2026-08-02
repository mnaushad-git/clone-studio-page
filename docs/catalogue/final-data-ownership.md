# Final Data Ownership (Catalogue Domain)

Phase 2B deliverable. Resolves `D17` in
[catalogue-decision-pack.md](catalogue-decision-pack.md). This is the concrete,
catalogue-scoped field-by-field split that supersedes the current (conflated)
`admin-store.ts` `ProductOverride` shape, directly implementing
[docs/architecture/data-ownership.md](../architecture/data-ownership.md) §4 and
[postgresql-field-mapping-draft.md](postgresql-field-mapping-draft.md) for the specific 26
products / 6 categories audited in this phase. No PostgreSQL tables or SQLAlchemy models
are created by this document — it is the specification those will implement in a later
phase.

## The rule

Every product field has exactly one owner. Odoo-owned fields are never editable from the
Admin Portal — they change only when the (not-yet-built) product-sync worker runs.
PostgreSQL/Admin-owned fields are never touched by Odoo sync.

## Odoo-owned fields — Admin must NOT permanently override

| Field | Canonical source today | Odoo target | Sync direction |
|---|---|---|---|
| SKU / internal reference | `products.json[].sku` (currently `PROPOSED`) | `product.product.default_code` | Odoo → Postgres |
| Product/variant identity | `products.json[].external_key` | `product.template` / `product.product` id | Odoo → Postgres (`odoo_product_id`) |
| Commercial name | `products.json[].name_en` | `product.template.name` | Odoo → Postgres |
| ERP description | `products.json[].description_en` | `product.template.description_sale` | Odoo → Postgres |
| Category | `products.json[].category_external_key` | `product.template.categ_id` | Odoo → Postgres |
| Base sales price | `products.json[].sales_price` | `product.template.list_price` | Odoo → Postgres (`product_price_cache`) |
| Tax mapping | `products.json[].tax_reference` (currently `null`, see `D08`) | `product.template.taxes_id` | Odoo → Postgres (`tax_rate_cache`) |
| Sellable / active status | `products.json[].active`/`.sellable` | `product.template.active` / `.sale_ok` | Odoo → Postgres |
| Unit of measure | `products.json[].unit_of_measure` (currently `null`, see `D09`) | `product.template.uom_id` | Odoo → Postgres |
| ERP inventory / on-hand qty | Not modeled (see `D19`) | `stock.quant` | Odoo → Postgres (`product_availability_cache`) |
| Primary product image | `products.json[].primary_image` | `product.template.image_1920` | One-time import (`D12`); afterward Odoo is authoritative if edited there |

**Rule:** the Admin Portal's product-edit screen must never expose an editable input for
any field in this table. If a business user needs to change one, the change happens in
Odoo and flows back through the product-sync worker — never the other way.

## PostgreSQL/Admin-owned fields — Admin may control directly

| Field | Canonical source today | Future table.column |
|---|---|---|
| Storefront visibility | `product-merchandising.json[].storefront_visible` | `product_merchandising.storefront_visible` |
| Featured flag | `product-merchandising.json[].featured` | `product_merchandising.featured` |
| Badge (New/Bestseller/etc.) | `product-merchandising.json[].badge_en/ar`, `.is_new`, `.is_bestseller` (see `D15`) | `product_merchandising.badges` |
| Display order | `product-merchandising.json[].display_order` (currently generated from array position) | `product_merchandising.display_order` |
| Homepage section membership | `product-merchandising.json[].homepage_sections` (see `D16` — not yet admin-configurable in practice) | `homepage_section` (join) |
| Moments | `product-merchandising.json[].moments` | `product_moment` (join table) |
| Recipients | `product-merchandising.json[].recipients` | `product_recipient` (join table) |
| Marketing title/description overrides | `product-merchandising.json[].marketing_title_en/ar`, `.marketing_description_en/ar` | `product_merchandising.marketing_*` |
| SEO title/description | `product-merchandising.json[].seo_title_en/ar`, `.seo_description_en/ar` | `product_merchandising.seo_*` |
| Storefront/mobile image overrides | `product-merchandising.json[].storefront_image_override`, `.mobile_image_override` | `product_merchandising.*_image_override` |
| Category display order/visibility | `categories.json[].display_order`, `.active` | `category.display_order`, `.active` (Admin-editable even though the category *identity* itself is Odoo-synced — see nuance below) |

**Rule:** the Admin Portal's product-edit screen writes only to `product_merchandising`
(and its join tables); it never has a code path that can set anything in the Odoo-owned
table above.

## Nuance: categories are split-owned too, not purely one side

Category **identity** (existence, `external_key`, commercial name) is Odoo-owned once
synced — same rule as products. But category **presentation** (`display_order`, `active`
i.e. whether it's shown in navigation) is genuinely Admin-owned today
(`admin-store.ts`'s `categories[].order/visible`) and should remain so — an Admin merchant
should be able to reorder or hide a storefront category tile without needing an Odoo change
request. This mirrors the product split exactly: `category` (Odoo-synced identity) vs. an
Admin-editable presentation layer, conceptually parallel to `product_merchandising`.

## Moments and Recipients — neither owner, by design

Per `data-ownership.md` and reaffirmed by this phase (`D02`'s scope note): Moments and
Recipients are **not** Odoo product categories and are **not** Odoo-owned at all. They are
PostgreSQL/Admin-owned vocabulary (`moment`, `recipient` tables) with their own
`product_moment`/`product_recipient` join tables, entirely independent of the Odoo product
category hierarchy. Odoo never sees them.

## What resolves the original audit finding

The Phase 2A audit found that `admin-store.ts`'s `ProductOverride` type conflates
`priceOverride`/`stock` (left-column, Odoo-owned) with `visible`/`featured`/`badge`/
`nameOverride`/`descriptionOverride` (right-column, Admin-owned) in one undifferentiated
object, and that no code path prevents an Admin edit to `priceOverride` from silently
diverging from Odoo's authoritative price. The two tables above are the direct fix: once
implemented as separate `product` and `product_merchandising` tables (a future phase, not
this one), it becomes structurally impossible for an Admin Portal request to write to an
Odoo-owned column, because that column simply won't exist in the table the Admin API writes
to.
