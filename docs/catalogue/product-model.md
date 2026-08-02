# Product Model

## Canonical structure (`data/catalogue/products.json`)

See [catalogue-data-dictionary.md](catalogue-data-dictionary.md) for the full field list.
This document explains the modeling decisions behind it.

## Identifier strategy

- **`slug`** reuses the product's existing `id` from `products.ts` (e.g.
  `"swiss-frosting"`, `"buttercream-cake"`). These ids are already kebab-case, already used
  as the live `/product/$id` route parameter, and are stable in practice (nothing in the
  app ever regenerates them). Per the instruction not to invent unstable identifiers where
  a good one already exists, they are reused as-is rather than re-minted.
- **`external_key`** = `terrific_bites.product.<slug>`, the convention specified for this
  phase — namespaces the identifier for Odoo external-id import (`ir.model.data`) and any
  future cross-system reference.
- **`sku`** does not exist anywhere in the current app. All 26 are generated using
  `TB-<CATEGORY-CODE>-<SEQUENCE>` (sequence = position within category, in the product's
  existing array order) and flagged `sku_generated: true` /
  `sku_requires_confirmation: true`. **None of these SKUs should be treated as final**
  until a business owner confirms them — see
  [catalogue-decisions-required.md](catalogue-decisions-required.md).

## Why "variants" is almost always null

Only **one** product (`buttercream-cake`) has size/flavor data defined directly on its
`Product` object in `products.ts` (`sizes: [...], flavors: [...]`). For the other 25
products, the size/flavor picker a shopper sees on the PDP is computed at render time in
`src/routes/product.$id.tsx` from **category-level default tables**
(`defaultSizesByCategory`, `defaultFlavorsByCategory`), with one further product-specific
exception hardcoded there (`sizeOverridesById["extra-icecream"]`).

This audit deliberately does **not** promote those category-level defaults into
per-product `variants` data in `products.json`, because doing so would fabricate
product-specific data that doesn't actually exist — every cupcake would appear to have
identical, independently-authored size data that is in fact one shared category default.
`products.json.variants` is therefore only populated for `buttercream-cake` (the one
product with genuine per-product structural data); the category-default behavior is
documented here and in
[catalogue-decisions-required.md](catalogue-decisions-required.md) as an open question for
whether it becomes real Odoo product-variant data (one variant per product per size) or
remains a client-presentation default with no Odoo/PostgreSQL backing at all.

## Description completeness is preserved as-is

15 of 26 products have `description_en: null`. Per the explicit instruction not to write
or invent product descriptions in this phase, no filler text was generated — the gap is
recorded as a `missing_description_en` validator warning instead.

## Currency and price

Preserved exactly as declared (`Product.price`, always rendered as `SAR X.XX` throughout
the UI). No currency conversion or rounding was applied. `tax_reference` is `null` for
every product — the only tax concept in the current app is a single site-wide 5%
`admin-store.settings.taxRate` applied at checkout, not a per-product tax class.

## Image handling

`primary_image` = the product's `image` import. `additional_images` is only non-empty for
`buttercream-cake` (whose `thumbs[]` includes 3 images beyond the primary). For every
other product, `product.$id.tsx` computes a *fallback* thumbnail rail from sibling
same-category product images at render time — again, computed presentation, not stored
per-product data, so it is not included in `additional_images`. Every image path was
checked against the actual filesystem and hashed (see
[image-inventory.md](image-inventory.md)); all 28 unique files referenced by the 26
products exist and are readable.

## Active/sellable/lifecycle

No product in the current app can be deactivated, hidden from sale, or marked
out-of-stock — there is no code path that reads such a flag. `active`/`sellable` are
therefore `true` for all 26 records, faithfully reflecting current reality rather than
inventing a lifecycle model that doesn't exist yet.
