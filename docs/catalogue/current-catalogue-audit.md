# Current Catalogue Audit

Phase 2A deliverable. Produced by inspecting the actual repository (not only
prior documentation) on 2026-07-27. Scope: analysis and data preparation only —
no application code, routes, or mock-data imports were changed.

## 1. Headline numbers

| Metric | Value |
|---|---|
| Catalogue data sources found | 15 (see [catalogue-source-inventory.md](catalogue-source-inventory.md)) |
| Products found in `src/lib/products.ts` | **26** |
| Unique products after dedup analysis | 26 (no duplicate ids, names, or images found) |
| Categories found | 6, but modeled independently in **3 separate places** (see §3) |
| Images referenced by the catalogue | 29 unique files (26 primary images, 1 per product, plus 3 additional thumbnail-only files on `buttercream-cake`) |
| Unused images (anywhere in the app) | 4 (`rel-1.jpg`..`rel-4.jpg`) |
| Missing/broken image files | 0 |
| Products without a confirmed SKU | 26 / 26 (no SKU concept exists in the app today) |
| Products missing an Arabic name | 26 / 26 |
| Products missing an Arabic description | 26 / 26 |
| Products missing an English description | 15 / 26 |

## 2. Correcting a stale number in prior documentation

[docs/current-state/mock-data.md](../current-state/mock-data.md) and
[docs/architecture/implementation-roadmap.md](../architecture/implementation-roadmap.md)
both state "28 products." Direct inspection (`grep -c '{ id:' src/lib/products.ts`)
confirms **26** product literals exist today. This audit treats the live
repository as ground truth per this phase's instructions; the "28" figure in
those docs is now stale and should be corrected when those docs are next
touched, but is out of scope to edit in this phase.

## 3. The three-sources-of-truth category problem, confirmed

Exactly as flagged in [target-architecture.md](../architecture/target-architecture.md) C8
and [implementation-roadmap.md](../architecture/implementation-roadmap.md) step 4, the
same 6 category slugs (`cupcakes, cakes, chocolates, donuts, gifts, extras`) are declared
independently in three places that could drift without anyone noticing:

1. `src/lib/products.ts` — `Category` union type + `CATEGORY_LABEL` map (no `id`, no `order`).
2. `src/lib/admin-store.ts` — `categories` seed array (has its own `id`, `slug`, `order`,
   `visible`) — admin-editable, but editing it does **not** change what categories
   `ShopGrid`'s sidebar filters by.
3. `src/components/ShopGrid.tsx` — its own hardcoded `CATEGORIES` array (with i18n label
   keys), completely independent of admin-store's list.

Today all three agree by coincidence, not by construction. The canonical
`data/catalogue/categories.json` produced by this phase is the single
reconciled source going forward (see [category-model.md](category-model.md)).

## 4. Product data completeness

Of 26 products:
- **11** have an English `description` (`swiss-frosting, moose-cream, butter-frosting,
  light-sponge, buttercream-cake, birthday-pair, butter-delight, cream-cheese-donut,
  whisk-whimsy, sprinkle-1, choc-truffle`).
- **15** have no description at all (`sprinkle-2/3/4`, all of `choc-praline` through
  `choc-berry` except `choc-truffle`, and all 4 `extra-*` products). These are recorded as
  `null` in `products.json`, not fabricated.
- **1** product (`swiss-frosting`) has `isNew: true`. No other new/bestseller flags exist
  anywhere in the app.
- **1** product (`buttercream-cake`) has explicit structural `sizes`/`flavors` and a
  `thumbs` gallery. All other products have neither — the size/flavor options a shopper
  sees on their PDP for those 25 products are computed on the fly from
  **category-level defaults** in `src/routes/product.$id.tsx`
  (`defaultSizesByCategory`/`defaultFlavorsByCategory`), not per-product data. This is a
  meaningful distinction for Odoo variant modeling — see
  [catalogue-decisions-required.md](catalogue-decisions-required.md).
- **0** products have a SKU, tax code, unit of measure, or stock/inventory value of any
  kind. `admin-store.ts`'s `ProductOverride.stock` field exists in the schema but its seed
  data (`productOverrides = {}`) is empty — no product has ever had a stock value set.
- **0** products have any Arabic content. The `i18n-dict/*` files translate UI chrome
  (buttons, labels, section headings) — product names/descriptions themselves are
  English-only string literals with no Arabic counterpart field anywhere in the type system.

## 5. Storefront vs. Admin Portal catalogue differences

- The Admin Portal has **no "add new product" capability** — `admin.products.tsx` can only
  edit/toggle existing products via `productOverrideStore`, layered on top of the
  `products.ts` array. Every product visible in the Storefront is therefore also visible in
  the Admin Portal, and vice versa — there is no set difference today.
- The Admin `ProductOverride` schema conflates **Odoo-owned commercial fields**
  (`priceOverride`, `stock`) with **PostgreSQL/Admin-owned merchandising fields**
  (`visible`, `featured`, `badge`, `nameOverride`, `descriptionOverride`) in one
  undifferentiated object — exactly the finding
  [data-ownership.md](../architecture/data-ownership.md) §4 calls out and prescribes
  splitting into `product` vs. `product_merchandising` tables.
- The Admin `categories` list order and the `products.ts` category set agree today (see §3)
  but are not the same underlying data.

## 6. Homepage merchandising is disconnected from admin configuration

- `src/routes/index.tsx`'s homepage rails (Products, Gifts, Divine treats, What's New,
  Event Catering, Cupcake Perfection) are entirely hardcoded against `featured.*` derived
  slices computed once at module load in `products.ts`. `admin-store.ts`'s
  `homepageSections` config (toggle/reorder UI in `/admin/content`) **has zero effect** on
  what actually renders — confirmed by direct inspection, matching
  [mock-data.md](../current-state/mock-data.md) line 55.
- A further bug found in this audit: the **"What's New" homepage section renders
  `featured.hero` a second time**, not `featured.new` — so the "What's New" rail today
  always shows the same 4 cupcakes as the "Products" rail, and the `isNew`-filtered slice
  (`featured.new`, which would correctly show only `swiss-frosting`) is computed but never
  displayed anywhere. Not fixed in this phase (rule: preserve existing UI behavior exactly),
  but recorded for [catalogue-migration-plan.md](catalogue-migration-plan.md).
- `featured.chocolates` and `featured.extras` (also computed in `products.ts`) are dead
  code from a rendering standpoint — no current homepage section reads them.

## 7. Moments and Recipients are not relationship tables

`OCCASIONS` (6: Birthday, Anniversary, Wedding, Graduation, Congratulations, Thank You) and
`RECIPIENTS` (4: For Him, For Her, For Kids, For Family) are hardcoded tuples in
`products.ts`. Each `Product` carries its own `occasions?: Occasion[]` and
`recipients?: Recipient[]` arrays; `/moments/$slug` and `/recipients/$slug` filter the full
product list client-side by array membership. There is no separate junction/mapping table
to migrate — the "mapping" *is* the per-product array. Canonicalized as
`moments.json`/`recipients.json` (the vocabulary) plus each product-merchandising record's
`moments`/`recipients` arrays (the membership), per
[data-ownership.md](../architecture/data-ownership.md)'s instruction not to force these
into Odoo product categories.

## 8. Recommendations are computed, not stored

`/product/$id`'s "Related products" section is
`products.filter(p => p.category === product.category && p.id !== product.id).slice(0, 4)`
— computed at render time, not sourced from any stored recommendation data.
"Recently viewed" (`src/lib/store.ts`) is a per-browser localStorage list, not a
product-to-product relationship. `data/catalogue/product-recommendations.json` therefore
ships **empty** with the schema documented, rather than materializing the current
same-category fallback as if it were curated business data (see
[product-recommendations.json](../../data/catalogue/product-recommendations.json)).

## 9. Reviews and ratings are out of catalogue scope

`src/lib/store.ts`'s 5 seeded reviews (`seededReviews`) and the review-derived average
rating (`selectAverageRating`) belong to the `reviews` domain in
[data-ownership.md](../architecture/data-ownership.md), not `catalogue` — they are noted
here for completeness but are not modeled in the canonical catalogue seed files. One
data-integrity quirk worth flagging for the eventual `reviews` module: `store.ts`'s
`load()` always re-merges the 5 seeded reviews back on top of localStorage on every load,
so an admin "delete review" action on a seeded review is not durable — see
[mock-data.md](../current-state/mock-data.md) line 31.

## 10. Validation result

`backend/scripts/validate_catalogue.py` run against the canonical seed files produced by
this phase: **0 blocking errors, 99 warnings** (all warnings are the missing-Arabic /
missing-description / generated-SKU gaps enumerated above — see
[catalogue-validation-report.json](../../data/catalogue/catalogue-validation-report.json)).
