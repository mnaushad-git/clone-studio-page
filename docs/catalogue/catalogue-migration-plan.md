# Catalogue Migration Plan

This is a **sequencing document**, not an implementation — it proposes how the canonical
seed data produced by this phase (Phase 2A) gets consumed by the roadmap steps that come
after it. Nothing here is implemented; no PostgreSQL tables, Odoo records, or FastAPI
routes exist yet. Numbering matches
[implementation-roadmap.md](../architecture/implementation-roadmap.md) where it overlaps.

## Step A — Business confirmation pass (blocks everything below)

Before any of `data/catalogue/*.json` touches Odoo or PostgreSQL, a human owner needs to
resolve every item in [catalogue-decisions-required.md](catalogue-decisions-required.md) —
most importantly the 26 generated SKUs and the category code convention, since those
become permanent external identifiers the moment they're imported anywhere. Cheap to
change now; expensive after Odoo import (roadmap step 5).

## Step B — Odoo catalogue import (roadmap step 5)

Using the confirmed version of `categories.json` and `products.json`:
1. Create 6 `product.category` records, keyed by `external_key` (idempotent re-run safe).
2. Create 26 `product.template` records (+ `product.product` variants where
   `product_type == "variant_parent"`, i.e. `buttercream-cake` only, unless Step A expands
   that scope), keyed by `external_key`.
3. Upload `primary_image` binaries to `image_1920`.
4. Leave Arabic name/description fields blank in Odoo (not fabricated) until Step A's
   translation gap is closed by the business.
5. Confirm via [odoo-field-mapping-draft.md](odoo-field-mapping-draft.md)'s open
   questions before writing any import script — this plan does not assume they're
   resolved.

## Step C — Odoo → PostgreSQL sync (roadmap step 6)

Once Step B exists, the `product_sync` worker's first run has real Odoo data to pull
(closing the "nothing to sync from" gap noted in
[integration-principles.md](../architecture/integration-principles.md) §2). The
`product`/`product_variant` PostgreSQL shape in
[postgresql-field-mapping-draft.md](postgresql-field-mapping-draft.md) becomes real
Alembic migrations at this point, not before.

## Step D — Merchandising/content seed (parallel to C, PostgreSQL-native, no Odoo dependency)

`product-merchandising.json`, `moments.json`, `recipients.json` do not depend on Odoo at
all — they can be loaded into PostgreSQL as soon as the `merchandising`/`content` domain
tables exist (roadmap step 9), independently of the Odoo sync timeline. `product_id`
foreign keys resolve against whatever `product.id` the sync worker assigned in Step C, via
the shared `external_key`.

## Step E — Catalogue API (roadmap step 7)

`/api/v1/products` reads the joined `product` + `product_merchandising` view. The known
gap from audit §6 (homepage rails hardcoded, admin config disconnected) should be resolved
here — either by wiring `homepage_sections` for real for the first time, or by an explicit
decision to redesign that config shape (see
[catalogue-decisions-required.md](catalogue-decisions-required.md)).

## Step F — Frontend cutover (roadmap step 8)

`ShopGrid`/`product.$id.tsx`/homepage rails switch from `products.ts` to the new API,
**with the UI visually unchanged** (rule 20). Two behavioral decisions must be made
explicitly before this step, not silently carried over:
- Whether the "What's New" rail keeps rendering `featured.hero` (preserving the current,
  arguably buggy, visual output byte-for-byte) or is corrected to show `is_new`-flagged
  products (a visible behavior change, requires sign-off even though it "fixes a bug").
- Whether the same-category "related products" fallback (audit §8) remains the
  recommendation strategy, or a real `product_recommendations` table is populated first.

## What this plan deliberately does not cover

Order/cart/checkout/payment/customer-auth flows — untouched by this phase, sequenced
separately in [implementation-roadmap.md](../architecture/implementation-roadmap.md) steps
10–18.
