# Catalogue Source Inventory

Every file inspected that contains, derives, or renders catalogue data, found by
inspecting the actual repository (imports, hardcoded arrays, admin stores, route usage) —
not by trusting a single mock-data file. 15 distinct sources.

## Primary data sources

| # | File | What it contributes |
|---|---|---|
| 1 | `src/lib/products.ts` | The catalogue: 26 products, `Category` union (6), `OCCASIONS` (6), `RECIPIENTS` (4), `CATEGORY_LABEL`, `featured.*` derived slices, slug helper functions. **The single point of truth for product existence.** |
| 2 | `src/lib/admin-store.ts` | `categories` (independent 6-entry seed with its own order/visibility), `productOverrides` (empty seed `{}`, schema for merchandising+commercial overrides), `homepageSections` (8 entries, unused by homepage), `banners` (2 entries, unused by homepage) |
| 3 | `src/components/ShopGrid.tsx` | Third independent `CATEGORIES` array; `OCCASION_LABEL_KEYS`/`RECIPIENT_LABEL_KEYS`; `PRICE_BUCKETS` (4 fixed price ranges); inline client-side search (name/description/category substring match) |
| 4 | `src/components/MegaMenu.tsx` | `CAT_IMG` — category-to-tile-image map (mega-menu navigation), reads `admin-store.categories` for visible/ordered rows |
| 5 | `src/components/ProductCard.tsx` | Renders `isNew` badge, price, description fallback, wishlist/cart affordances — no new data, but is a consumer whose display contract constrains the canonical fields |
| 6 | `src/components/ProductReviews.tsx` | Reviews UI (out of catalogue scope, see audit §9) |
| 7 | `src/routes/product.$id.tsx` | `defaultSizesByCategory`/`defaultFlavorsByCategory`/`sizeOverridesById` — category-level (and one product-level: `extra-icecream`) presentational variant defaults; related-products and recently-viewed computation |
| 8 | `src/routes/shop.tsx`, `cakes.tsx`, `cupcakes.tsx`, `chocolates.tsx`, `donuts.tsx`, `gifts.tsx`, `extras.tsx` | Per-category SEO `<meta>` title/description text — the only source of category-level descriptive copy in the whole app |
| 9 | `src/routes/index.tsx` | Homepage rail composition (`featured.hero/gifts/divine`), hardcoded and disconnected from `admin-store.homepageSections` |
| 10 | `src/routes/moments.index.tsx`, `moments.$slug.tsx` | `OCCASION_HERO` — subtitle/blurb i18n keys + accent emoji per occasion |
| 11 | `src/routes/recipients.index.tsx`, `recipients.$slug.tsx` | Recipient listing/filtering (no additional data beyond `RECIPIENTS` tuple) |
| 12 | `src/routes/admin.products.tsx` | Admin product list/editor — reads `products.ts` + `productOverrideStore`; the `ProductEditor` form is the de facto schema for all mutable merchandising+commercial fields today |
| 13 | `src/routes/admin.categories.tsx` | Admin category CRUD against `admin-store.categories` — independent of `products.ts`'s `Category` type (adding a category here would not make `ShopGrid` or `product.$id.tsx` aware of it) |
| 14 | `src/routes/admin.content.tsx` | Admin banners + homepage-sections CRUD — confirmed to have zero effect on the actual homepage (audit §6) |
| 15 | `src/assets/*.jpg` | 28 unique image files imported by `products.ts` and category/homepage chrome — see [image-inventory.md](image-inventory.md) |

## Consumers checked but contributing no additional catalogue data

- `src/components/CartDrawer.tsx`, `src/lib/store.ts` — read `getProduct()`/`productMap`
  for cart/order line items; no new product fields.
- `src/routes/wishlist.tsx` — reads `getProduct()` for wishlist ids; no new fields.
- `src/routes/admin.analytics.tsx`, `admin.reviews.tsx`, `admin.index.tsx` — read product
  names/ids for display only.

## Non-catalogue asset sources (out of scope, confirmed by usage grep)

`about-banner.jpg`, `about-testimonial.jpg`, `about-vision.jpg`, `catering.jpg`,
`gift-card*.jpg` (customize.tsx gift-card picker), `hero-cupcake.jpg`, `person-donut.jpg`,
`signup-illustration.jpg`, `logo-footer.png.asset.json` — all used exclusively by
non-catalogue pages (`about.tsx`, `customize.tsx`, `signup.tsx`, homepage decorative
sections, `SiteFooter`) or as the mega-menu's "Moments"/"Recipients" tile images. Not
modeled in the canonical product/category image inventory.

## Explicitly checked and confirmed absent

- No dedicated `/search` route or search API — search is `ShopGrid`'s inline client-side
  filter (see #3 above).
- No JSON data files anywhere in `src/` (`find src -iname "*.json"` returns only a Lovable
  asset-metadata sidecar, `src/assets/logo-footer.png.asset.json`, not catalogue data).
- No Supabase table or query touches product/category data (`src/integrations/supabase/*`
  is unwired, matching [target-architecture.md](../architecture/target-architecture.md)).
- No hardcoded product arrays exist outside `src/lib/products.ts` itself — all other files
  either import from it or apply overrides on top of it.
