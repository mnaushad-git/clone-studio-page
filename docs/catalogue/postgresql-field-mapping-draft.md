# PostgreSQL Field Mapping (Draft)

**Draft only — no migrations or SQLAlchemy models are created in this phase.** Proposes
domain-level entities consistent with
[data-ownership.md](../architecture/data-ownership.md) §1's `catalogue`/`merchandising`/
`content` domain boundaries. Table/column names here are illustrative, not final DDL.

## `catalogue` domain

### `product` (Odoo-synced cache — never written by Admin Portal directly)

| Column | Source (canonical JSON) | Notes |
|---|---|---|
| `id` (PK) | — | Internal surrogate key |
| `odoo_product_id` | — | Set by product-sync worker once Odoo import (roadmap step 5) exists; `null` until then |
| `external_key` | `products.json[].external_key` | Unique, used for idempotent upsert before `odoo_product_id` exists |
| `sku` | `products.json[].sku` | Synced from Odoo `default_code` once live; canonical file's generated value is the pre-Odoo seed only |
| `slug` | `products.json[].slug` | Drives the existing `/product/$id` route without changing it |
| `name` | `products.json[].name_en` | `[VERIFY]` whether a separate `name_ar` column or an i18n-string pattern is used, once Arabic product content exists |
| `description` | `products.json[].description_en` | |
| `category_id` | FK → `category.id`, via `products.json[].category_external_key` | |
| `base_price` (→ `product_price_cache`) | `products.json[].sales_price` | Per rule 9, kept in its own cache table with `synced_at`, not on `product` itself, once real Odoo sync exists |
| `currency` | `products.json[].currency` | |
| `tax_class` (→ `tax_rate_cache`) | `products.json[].tax_reference` (currently `null`) | |
| `is_active` | `products.json[].active` | |
| `primary_image_url` | `products.json[].primary_image` | Object-storage URL once images are migrated off bundled assets; `original_path` preserved as provenance |

### `product_variant`

| Column | Source | Notes |
|---|---|---|
| `id` (PK), `product_id` (FK) | — | |
| `odoo_variant_id` | — | Set by sync worker |
| `label`, `sub_label`, `price_delta` | `products.json[].variants.sizes[]` | Only populated for `buttercream-cake` today (see [product-model.md](product-model.md)) |
| `flavor` | `products.json[].variants.flavors[]` | |

### `product_availability_cache`

Not populated by this phase at all — no inventory/stock concept exists in the current
mock data (`ProductOverride.stock` schema field, seed always unset).

## `merchandising` domain

### `product_merchandising` (Admin-Portal-owned; never touched by Odoo sync)

| Column | Source |
|---|---|
| `product_id` (FK) | `product-merchandising.json[].product_external_key` |
| `storefront_visible` | `.storefront_visible` |
| `featured` | `.featured` |
| `is_new`, `is_bestseller` | `.is_new`, `.is_bestseller` (latter always `null` — no concept exists yet) |
| `badge_en`, `badge_ar` | `.badge_en`, `.badge_ar` |
| `display_order` | `.display_order` (generated placeholder, needs confirmation before treating as real ordering) |
| `marketing_title_en/ar`, `marketing_description_en/ar` | `.marketing_*` (all `null` today) |
| `seo_title_en/ar`, `seo_description_en/ar` | `.seo_*` (all `null` today) |
| `storefront_image_override`, `mobile_image_override` | `.storefront_image_override`, `.mobile_image_override` |
| `updated_by_admin_id`, `updated_at` | New columns — no equivalent audit trail exists in current `admin-store.ts` |

### `homepage_section` / `banner`

Proposed shape mirrors `admin-store.ts`'s existing `homepageSections`/`banners` types
(`id`, `label`, `visible`, `order` / `title`, `subtitle`, `cta_label`, `cta_link`, `image`,
`position`, `active`, `order`) — **but** per audit §6, the current shape has never actually
driven the homepage. Recommend the future `merchandising` module either (a) wire the
existing shape to real rendering for the first time (closing roadmap step 9's gap) or
(b) redesign the shape alongside that wiring — a decision for that phase, not this one.

## `content` domain

### `moment` / `recipient`

| Column | Source |
|---|---|
| `id` (PK) | — |
| `external_key` | `moments.json[].external_key` / `recipients.json[].external_key` |
| `slug`, `name_en`, `name_ar` | direct mapping |
| `accent_emoji` (moment only) | `moments.json[].accent_emoji` |
| `display_order`, `active` | direct mapping |

### Product ↔ moment / recipient association

A join table (`product_moment`, `product_recipient`) populated from each
`product-merchandising.json[].moments`/`.recipients` array — replaces the current
client-side `Product.occasions[]`/`recipients[]` filtering with real relational rows,
without changing what a shopper sees.

## Not modeled (deferred to future recommendation-engine scoping)

`product_recommendations` table shape is documented in
[product-recommendations.json](../../data/catalogue/product-recommendations.json)'s
`schema` key but intentionally not instantiated here, since no real recommendation data
exists to seed it with (see [current-catalogue-audit.md](current-catalogue-audit.md) §8).
