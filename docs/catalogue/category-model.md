# Category Model

## Canonical structure (`data/catalogue/categories.json`)

```
external_key            terrific_bites.category.<slug>
code                    3-letter SKU-prefix code (generated, requires confirmation)
slug                    URL segment (e.g. "cupcakes")
name_en / name_ar
description_en / description_ar
parent_external_key     null for all 6 today — catalogue is flat
active
display_order
source_references[]
requires_confirmation[]
```

## The 6 categories

| slug | code (generated) | name_en | display_order |
|---|---|---|---|
| cupcakes | CUP | Cupcakes | 1 |
| cakes | CAK | Cakes | 2 |
| chocolates | CHO | Chocolates | 3 |
| donuts | DON | Donuts | 4 |
| gifts | GIF | Gifts | 5 |
| extras | EXT | Extras | 6 |

## Why these 6 and not a hierarchy

`products.ts`'s `Category` TypeScript union is a flat 6-value enum; nothing in the
codebase implies a parent/child category relationship (no subcategories, no
"category groups" anywhere in routes, admin UI, or navigation). `parent_external_key`
is included in the canonical schema for forward-compatibility (Odoo's `product.category`
supports hierarchy) but is `null` for all 6 records — introducing hierarchy is a business
decision, not something this audit can infer.

## Reconciling the three existing sources

As detailed in [current-catalogue-audit.md](current-catalogue-audit.md) §3, this exact
6-slug set is declared independently in `products.ts`, `admin-store.ts`, and
`ShopGrid.tsx`. All three agree on slugs and English labels today. `categories.json`'s
`display_order` is taken from `admin-store.ts` (the only one of the three with an explicit
order field); `description_en` is taken from each category route's SEO
`<meta name="description">`, since none of the three category lists themselves carry a
description field.

## Known gap: "extras" has no dedicated navigation image

`MegaMenu.tsx`'s `CAT_IMG` map has an entry for every category except `extras`, which
falls back to reusing the `gifts` tile image (`gift-donuts.jpg`). Recorded as a
`requires_confirmation` flag on the `extras` category record — not fixed here, since fixing
it would change rendered UI (out of Phase 2A scope).

## What is intentionally NOT in this model

Per [data-ownership.md](../architecture/data-ownership.md), Moments and Recipients are
**not** categories and are **not** forced into this hierarchy — they are separate
vocabulary entities (`moments.json`, `recipients.json`) with their own external-key
namespace, matched to the architecture's explicit instruction not to conflate them with
Odoo product categories.
