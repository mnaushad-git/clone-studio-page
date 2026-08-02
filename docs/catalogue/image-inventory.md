# Image Inventory

`src/assets/` contains 46 files: 45 images (`.jpg`/`.png`) plus 1 Lovable asset-metadata
sidecar (`logo-footer.png.asset.json`, not an image itself). All 45 images were checked
against every `import` in the codebase (`grep -rl <basename> src`).

## 1. Catalogue images — 29 unique files (all exist, all verified, 0 broken)

Every file referenced by `src/lib/products.ts`, checked for existence, size, and MD5
checksum (recorded in `data/catalogue/products.json`). No missing or broken image paths
were found.

| Category | Files | Count |
|---|---|---|
| Cupcakes | `prod-swiss.jpg`, `prod-moose.jpg`, `prod-butter.jpg`, `prod-light.jpg`, `divine-1.jpg`, `divine-2.jpg`, `divine-3.jpg`, `divine-4.jpg` | 8 |
| Cakes | `cake-main.jpg` (primary), `cake-thumb-2.jpg`, `cake-thumb-3.jpg`, `cake-thumb-4.jpg` (gallery-only) | 4 |
| Gifts | `gift-donuts.jpg`, `gift-butter.jpg`, `gift-whisk.jpg` | 3 |
| Donuts | `gift-cream.jpg` (used by `cream-cheese-donut`, despite the filename) | 1 |
| Chocolates | `choc-1.jpg` through `choc-9.jpg` | 9 |
| Extras | `extra-donut.jpg`, `extra-icecream.jpg`, `extra-cheesecake.jpg`, `extra-donuts-pair.jpg` | 4 |
| **Total** | | **29** |

No two products share a primary image; no product's primary image filename is misleading
except the one noted above (`gift-cream.jpg` → `cream-cheese-donut`, a `donuts`-category
product using a filename that reads like a `gifts` asset — a naming inconsistency worth
flagging, not a functional bug).

## 2. Non-catalogue site/marketing images — 12 files (confirmed in use, out of catalogue scope)

| File | Used by |
|---|---|
| `hero-cupcake.jpg` | Homepage hero, MegaMenu "Moments" tile |
| `catering.jpg` | Homepage "Event Catering" section |
| `donuts-hero.jpg` | MegaMenu "Donuts" category tile, About page, Homepage |
| `person-donut.jpg` | Homepage "Cupcake Perfection" section, About page |
| `about-banner.jpg`, `about-testimonial.jpg`, `about-vision.jpg` | About page only |
| `signup-illustration.jpg` | Signup page only |
| `gift-card.jpg`, `gift-card-brown.jpg`, `gift-card-cream.jpg`, `gift-card-red.jpg` | Customize/gift-card-message page (`customize.tsx`) |

These are site chrome/marketing assets, not product or category data, and are not
represented in the canonical catalogue JSON files.

## 3. Unused images — 4 files

`rel-1.jpg`, `rel-2.jpg`, `rel-3.jpg`, `rel-4.jpg` — not imported by any `.ts`/`.tsx` file
in the repository (`grep -rl` returns zero matches for each). Likely leftover from an
earlier Lovable iteration (possibly a "related products" feature, given the filename
prefix). Not deleted in this phase per the "do not remove or replace existing product
images" / "do not move or rename existing image files" rules — flagged here for a human
decision on cleanup.

## 4. Category navigation image gap

`MegaMenu.tsx`'s `CAT_IMG` map has no dedicated tile image for the `extras` category — it
falls back to reusing `gift-donuts.jpg` (the `gifts` tile image). Recorded as a
`requires_confirmation` flag on the `extras` category record in `categories.json`.

## 5. Checksums

Every catalogue image's MD5 checksum was computed and stored in `products.json` at
generation time (field: `checksum`, format `md5:<hex>`) for future drift detection once
images move to object storage. No two catalogue images share a checksum (no duplicate
image reuse across different products).
