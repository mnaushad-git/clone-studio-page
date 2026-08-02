# Catalogue Field Ownership Classification

Every discovered field classified per the Phase 2A instructions into one of: Odoo-owned
ERP data, PostgreSQL/Admin-owned storefront data, Derived data, Temporary/mock-only data,
Requires business decision. Cross-references
[docs/architecture/data-ownership.md](../architecture/data-ownership.md), which this
classification is designed to slot directly into.

## 1. Odoo-owned ERP data (future authoritative source: Odoo)

| Field | Current mock source |
|---|---|
| Product identity / variant identity | `products.ts` product literal (id) |
| SKU / internal reference | Does not exist — must be created in Odoo import, see [odoo-field-mapping-draft.md](odoo-field-mapping-draft.md) |
| Commercial product name | `Product.name` |
| ERP description | `Product.description` (11/26 populated) |
| Product category | `Product.category` |
| Base sales price | `Product.price` |
| Tax mapping | Does not exist per-product — only a site-wide 5% `taxRate` in `admin-store.settings` |
| Sellable / active status | Does not exist — implicitly always true today |
| Unit of measure | Does not exist |
| ERP inventory/availability | Does not exist — `ProductOverride.stock` schema field exists but every seed value is unset |
| Primary product image | `Product.image` |

## 2. PostgreSQL/Admin-owned storefront data (future authoritative source: Admin Portal → PostgreSQL)

| Field | Current mock source |
|---|---|
| Featured flag | `ProductOverride.featured` (schema exists, seed empty) |
| Homepage section membership | Currently hardcoded in `index.tsx` via `featured.*` slices, NOT the admin `homepageSections` config (see audit §6) — this is the single biggest ownership gap to close in a future phase |
| Storefront display order | Does not exist per-product; generated here from array position |
| Marketing badge | `ProductOverride.badge` (schema exists, seed empty) |
| Marketing title/description override | `ProductOverride.nameOverride`/`descriptionOverride` (schema exists, seed empty) |
| Moment mapping | `Product.occasions[]` |
| Recipient mapping | `Product.recipients[]` |
| Product recommendations | Does not exist (computed fallback only, see audit §8) |
| SEO title/description | Does not exist |
| Storefront visibility | `ProductOverride.visible` (schema exists, seed always `true`) |
| Storefront/mobile image override | `ProductOverride.imageOverride` (schema exists, seed empty); "mobile-specific image" has no concept anywhere |
| Category display order, visibility | `admin-store.categories[].order/visible` |
| Moments/Recipients vocabulary itself | `OCCASIONS`/`RECIPIENTS` tuples — per instructions, NOT forced into Odoo product categories |

## 3. Derived data (computed, not stored anywhere as source-of-truth)

| Field | Derivation |
|---|---|
| `featured.hero/gifts/divine/chocolates/extras/new` | `.filter()`/`.slice()` over `products.ts` at module load |
| Homepage rail membership (as captured in `product-merchandising.json`) | Snapshot of the above at generation time |
| Category-level default size/flavor options | Computed per-render in `product.$id.tsx`, keyed by category, not stored per product |
| Related products ("recommendations") | Same-category slice computed per-render |
| Average product rating | Computed from `reviews[]` at render time |

## 4. Temporary/mock-only data (not part of the catalogue's future model at all)

- `admin-store.ts`'s `homepageSections`/`banners` seeds, given they have zero effect on
  the actual homepage today — these belong to a future `merchandising`/`content` module
  redesign, not a straight lift of the current (disconnected) config shape.
- `admin-store.ts`'s `productOverrides` object shape itself (conflated
  commercial+merchandising fields) — superseded by the `product`/`product_merchandising`
  split in [data-ownership.md](../architecture/data-ownership.md) §4.
- Seeded reviews (`store.ts`) — belongs to the `reviews` domain, not `catalogue`.

## 5. Requires business decision (cannot be classified from code alone)

See [catalogue-decisions-required.md](catalogue-decisions-required.md) for the full list
with recommendations; summarized here for the ownership matrix:

- SKU values (currently all `sku_generated: true`)
- Category codes used in the SKU convention
- Tax mapping / tax class per product (vs. the current single site-wide rate)
- Unit of measure per product
- Whether category-level default size/flavor options become real Odoo product variants
  per product, or remain a PostgreSQL/Admin-owned presentation default
- `is_bestseller` — whether/how this concept should exist at all
- Whether the homepage-rail-membership captured here becomes the seed for a real
  `homepage_section` PostgreSQL table, or is discarded in favor of a redesigned admin-driven
  homepage config
