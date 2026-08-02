# Catalogue Data Dictionary

Field-by-field reference for the seven canonical JSON files under `data/catalogue/`.
Every field lists: meaning, current value source, and status
(`confirmed` = taken directly from existing code with no ambiguity;
`generated` = computed by this phase, not present in source, needs business confirmation;
`missing` = genuinely absent, stored as `null`).

## categories.json

| Field | Meaning | Status |
|---|---|---|
| `external_key` | `terrific_bites.category.<slug>` — stable cross-system identifier | generated (convention applied, slug itself is confirmed) |
| `code` | 3-letter SKU-prefix code (`CUP`, `CAK`, `CHO`, `DON`, `GIF`, `EXT`) | generated, requires confirmation |
| `slug` | URL segment, e.g. `/cupcakes` | confirmed (`src/lib/products.ts` `Category` union) |
| `name_en` | Display label | confirmed (`CATEGORY_LABEL`) |
| `name_ar` | Arabic display label | missing |
| `description_en` | Category-level marketing copy | confirmed (category route `<meta name="description">`) |
| `description_ar` | Arabic category copy | missing |
| `parent_external_key` | Parent category, for hierarchy | confirmed `null` — catalogue is flat today |
| `active` | Whether category is live | confirmed `true` for all 6 |
| `display_order` | Sort position | confirmed (`admin-store.ts` categories seed `order`) |
| `source_references` | Files this record was derived from | generated (audit trail) |
| `requires_confirmation` | Flags for business sign-off | generated |

## products.json

| Field | Meaning | Status |
|---|---|---|
| `external_key` | `terrific_bites.product.<slug>` | generated (slug confirmed = existing `id`) |
| `sku` / `sku_generated` / `sku_requires_confirmation` | Proposed `TB-<CODE>-<SEQ>` SKU; always `true`/`true` today since no SKU exists anywhere in the app | generated |
| `slug` | = the product's existing `id` in `products.ts` (already kebab-case and used as the `/product/$id` route param — reused rather than re-minted, per the instruction not to invent new unstable identifiers) | confirmed |
| `name_en` | Product display name | confirmed |
| `name_ar` | Arabic name | missing (26/26) |
| `description_en` | Product description | confirmed where present, `null` for 15/26 |
| `description_ar` | Arabic description | missing (26/26) |
| `short_description_en/ar` | Separate short-form copy | missing — no such field exists in the current app |
| `category_external_key` | FK to `categories.json` | confirmed |
| `sales_price` | Current price | confirmed (`product.price`), currency always SAR |
| `currency` | ISO-ish currency label | confirmed `"SAR"` (the only currency ever rendered in the UI) |
| `tax_reference` | Product-level tax class | missing — only a single site-wide `taxRate` (5%) exists in `admin-store.settings`, not per-product |
| `active` / `sellable` | Lifecycle flags | confirmed `true`/`true` — no inactive/unsellable concept exists today |
| `product_type` | `"simple"` or `"variant_parent"` | generated classification based on presence of literal `sizes`/`flavors` on the product object (only `buttercream-cake` qualifies) |
| `unit_of_measure` | e.g. "each", "box of 6" | missing — no such field exists |
| `primary_image` / `additional_images` | Image metadata objects, see below | confirmed (path/size/checksum verified against disk) |
| `variants` | Literal `sizes`/`flavors` arrays, only non-null for `buttercream-cake` | confirmed; category-level *default* size/flavor options are deliberately NOT included here (see [product-model.md](product-model.md)) |
| `is_new_flag_raw` | Raw `Product.isNew` | confirmed |
| `occasions_raw` / `recipients_raw` | Raw arrays as declared on the product | confirmed |
| `source_references` / `requires_confirmation` | Audit trail / confirmation flags | generated |

### Image object (`primary_image`, `additional_images[]`)

| Field | Meaning |
|---|---|
| `original_path` | Repo-relative path, e.g. `src/assets/prod-swiss.jpg` |
| `original_filename` | Bare filename |
| `source_type` | Always `"local_asset_import"` today (no remote image URLs exist anywhere in the catalogue) |
| `exists` | Verified against disk at generation time |
| `file_size` | Bytes |
| `file_extension` | e.g. `jpg` |
| `usage` | `"primary_product_image"` or `"gallery_thumbnail"` |
| `alt_text_en` / `alt_text_ar` | English alt text = product name; Arabic missing |
| `checksum` | `md5:<hex>` of file contents, computed at generation time |

## product-merchandising.json

| Field | Meaning | Status |
|---|---|---|
| `product_external_key` | FK to `products.json` | confirmed |
| `storefront_visible` | Confirmed `true` for all — no product has `visible: false` in the (empty) `productOverrides` seed | confirmed |
| `featured` | Confirmed `false` for all — the admin `featured` toggle is never set in the seed; distinct from homepage rail membership (see `homepage_sections` below) | confirmed |
| `is_new` | = `products.json`'s `is_new_flag_raw` | confirmed |
| `is_bestseller` | No such concept exists anywhere in the app | missing, requires business decision |
| `badge_en` / `badge_ar` | Admin `ProductOverride.badge` field; never set in seed data | missing |
| `display_order` | Sequential position in `products.ts`'s array (1–26) | generated, requires confirmation |
| `homepage_sections` | Which homepage rail(s) the product currently appears in, derived from `featured.hero/gifts/divine` | generated (derived from live code, but the mapping itself — which rails exist and what feeds them — is admin-inconfigurable today; see [current-catalogue-audit.md](current-catalogue-audit.md) §6) |
| `moments` / `recipients` | FKs into `moments.json`/`recipients.json`, from the product's raw `occasions`/`recipients` arrays | confirmed |
| `marketing_title_en/ar`, `marketing_description_en/ar` | Admin override fields; never set in seed | missing |
| `seo_title_en/ar`, `seo_description_en/ar` | No per-product SEO override field exists (page `<title>`/`<meta>` are computed from name/description directly) | missing |
| `storefront_image_override` / `mobile_image_override` | Admin `imageOverride` field exists in schema but never set; no "mobile-specific image" concept exists anywhere | missing |

## moments.json / recipients.json

Vocabulary tables for the `OCCASIONS`/`RECIPIENTS` tuples in `products.ts`. `accent_emoji`
(moments only) is real UI content from `moments.$slug.tsx`'s `OCCASION_HERO`, preserved
because it's actual current presentation data, not a fabrication.

## product-recommendations.json

Ships empty by design — see [current-catalogue-audit.md](current-catalogue-audit.md) §8.
Schema documented for future use.

## catalogue-validation-report.json

Generated (not hand-authored) by `backend/scripts/validate_catalogue.py`. Structure:
`generated_at`, `status` (`pass`/`fail`), `summary` (`total_issues`/`errors`/`warnings`),
`issues[]` (`severity`, `code`, `message`, `entity`).
