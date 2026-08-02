# Catalogue Decisions Required

Every item here needs a human business decision before the canonical seed data can be
treated as final. Nothing in this list was resolved unilaterally by this audit — where a
value had to be produced to make the schema complete, it was generated and explicitly
flagged `requires_confirmation` in the JSON rather than presented as authoritative.

## Blocking (should be resolved before Odoo import, Step B of the migration plan)

1. **All 26 SKUs are generated, not business-assigned.** Convention used:
   `TB-<CATEGORY-CODE>-<SEQUENCE>`, sequence = current array order within category. Needs
   sign-off on both the convention and the actual sequence (e.g. should
   `buttercream-cake`, the highest-value item, be `TB-CAK-001` regardless of catalogue
   order, or does sequence encode something meaningful like launch date?).
2. **Category codes are generated, not business-assigned**: `CUP/CAK/CHO/DON/GIF/EXT`.
   Any change here cascades into every SKU.
3. **Tax mapping.** Today there is exactly one site-wide 5% VAT rate
   (`admin-store.settings.taxRate`) applied at checkout — no per-product or per-category
   tax class exists. Decide: is a single tax class sufficient for the Odoo import (likely,
   for a single-country single-VAT-rate business), or do specific product types (e.g.
   catering/corporate orders) need different tax treatment?
4. **Unit of measure.** No UoM concept exists anywhere in the current app. Odoo requires
   one per product template. Likely "Units" for everything, but needs confirmation,
   especially for size-variant products like `buttercream-cake`.

## Important (affects data model shape, resolve before Step C/D)

5. **Category-level default size/flavor options — promote to real variants, or keep as
   presentation-only?** Only `buttercream-cake` has genuine per-product variant data
   today; every other cupcake/chocolate/donut/gift/extra's size and flavor picker is a
   shared category-level default computed client-side
   (`defaultSizesByCategory`/`defaultFlavorsByCategory` in `product.$id.tsx`). If the
   business wants per-product Odoo variants (e.g. so inventory/pricing can differ by size
   per product), this needs to be explicitly modeled and populated — it is currently
   `null` for 25/26 products by design, not by omission.
6. **`is_bestseller` — does this concept exist at all?** No such flag exists anywhere in
   the current app (unlike `isNew`, which does). Needs a decision on whether to introduce
   it, and if so, how it's computed/assigned (manually by admin, or derived from order
   volume).
7. **Homepage rail / `homepage_sections` redesign.** The current `admin-store.homepageSections`
   config has zero effect on the actual homepage (confirmed by direct inspection); the
   real rails are hardcoded `featured.*` slices in `products.ts`, one of which
   (`featured.new`) is dead code and another slot ("What's New") actually duplicates the
   "Products" rail due to a bug. Decide: wire the existing config shape for real, or
   redesign it as part of roadmap step 9 — either way, this is not a straight lift of
   current (non-functional) admin config.
8. **Product recommendations.** No curated recommendation data exists; `product-recommendations.json`
   ships empty. Decide whether the same-category fallback stays as the permanent strategy,
   or a real curation/recommendation-engine feature gets scoped.

## Lower priority (content gaps, not structural)

9. **Arabic product names and descriptions — all 26 products, all 6 categories, all 6
   moments, all 4 recipients have no Arabic content.** This is a translation/content
   project, not a data-modeling question, but it blocks true bilingual parity for the
   catalogue (the rest of the UI chrome is already bilingual via `i18n-dict/*`).
10. **15 of 26 products have no English description at all** (see
    [product-model.md](product-model.md)). Needs copywriting, not data engineering.
11. **`extras` category has no dedicated navigation tile image** (reuses the `gifts`
    image). Low-priority cosmetic gap.
12. **4 unused image files** (`rel-1.jpg`..`rel-4.jpg`) — confirm safe to delete in a
    future cleanup pass (not done here, per this phase's "do not remove/move existing
    images" constraint).
13. **`gift-cream.jpg` names a `donuts`-category product** (`cream-cheese-donut`) despite
    reading as a `gifts` asset — purely a filename/organization inconsistency, no
    functional impact.

## Explicitly NOT a decision needed (resolved by architecture docs already)

- Moments/Recipients are confirmed **not** to become Odoo product categories — already
  settled by [data-ownership.md](../architecture/data-ownership.md).
- No multi-tenant/currency-per-city work is in scope for this catalogue — carried forward
  as [implementation-roadmap.md](../architecture/implementation-roadmap.md) open question
  #8, not re-litigated here.
