# Identifier Mapping Register

Phase 2B deliverable. Resolves item 20 ("Primary product identifier mapping") and
[catalogue-decisions.json](../../data/catalogue/catalogue-decisions.json) `D20`. One row
per product, giving every identifier/attribute an implementer needs to write the eventual
Odoo import script, with no ambiguity about which value came from where.

**No canonical seed file was changed to produce this table** — every column below is
either already present in [products.json](../../data/catalogue/products.json) /
[categories.json](../../data/catalogue/categories.json), or is a direct, deterministic
derivation from them (the "Proposed Odoo identifier strategy" column).

## Odoo external-id strategy (applies to every row)

Per `D20`, every product/category is imported using Odoo's standard external-id mechanism
(`ir.model.data`), keyed by a single module namespace:

```
xml_id = terrific_bites.product_<slug>       (products)
xml_id = terrific_bites.category_<slug>      (categories)
```

This makes import/re-import idempotent (rule 7): re-running the import against the same
`xml_id` updates the existing record instead of duplicating it. `external_key` (already in
the canonical JSON) and `xml_id` carry the same information in two conventional forms —
`external_key` for our own systems, `xml_id` for Odoo's.

## Full table (26/26 products)

| Frontend `id` | Product external key | SKU (proposed) | Slug | Name (EN) | Category code | Current image path | Proposed Odoo xml_id | Confirmation status |
|---|---|---|---|---|---|---|---|---|
| `swiss-frosting` | `terrific_bites.product.swiss-frosting` | `TB-CUP-001` | `swiss-frosting` | Swiss Frosting | CUP | `src/assets/prod-swiss.jpg` | `terrific_bites.product_swiss-frosting` | SKU: PROPOSED |
| `moose-cream` | `terrific_bites.product.moose-cream` | `TB-CUP-002` | `moose-cream` | Moose Cream | CUP | `src/assets/prod-moose.jpg` | `terrific_bites.product_moose-cream` | SKU: PROPOSED |
| `butter-frosting` | `terrific_bites.product.butter-frosting` | `TB-CUP-003` | `butter-frosting` | Butter Frosting | CUP | `src/assets/prod-butter.jpg` | `terrific_bites.product_butter-frosting` | SKU: PROPOSED |
| `light-sponge` | `terrific_bites.product.light-sponge` | `TB-CUP-004` | `light-sponge` | Light Sponge | CUP | `src/assets/prod-light.jpg` | `terrific_bites.product_light-sponge` | SKU: PROPOSED |
| `buttercream-cake` | `terrific_bites.product.buttercream-cake` | `TB-CAK-001` | `buttercream-cake` | Buttercream Cake | CAK | `src/assets/cake-main.jpg` (+3 gallery thumbs) | `terrific_bites.product_buttercream-cake` | SKU: PROPOSED; variants: APPROVED (D11) |
| `birthday-pair` | `terrific_bites.product.birthday-pair` | `TB-GIF-001` | `birthday-pair` | Birthday Pair Cups | GIF | `src/assets/gift-donuts.jpg` | `terrific_bites.product_birthday-pair` | SKU: PROPOSED |
| `butter-delight` | `terrific_bites.product.butter-delight` | `TB-GIF-002` | `butter-delight` | Butter Frosting Delight | GIF | `src/assets/gift-butter.jpg` | `terrific_bites.product_butter-delight` | SKU: PROPOSED |
| `cream-cheese-donut` | `terrific_bites.product.cream-cheese-donut` | `TB-DON-001` | `cream-cheese-donut` | Cream & Cheese Donut | DON | `src/assets/gift-cream.jpg` (naming quirk, see D12) | `terrific_bites.product_cream-cheese-donut` | SKU: PROPOSED |
| `whisk-whimsy` | `terrific_bites.product.whisk-whimsy` | `TB-GIF-003` | `whisk-whimsy` | Whisk & Whimsy Cupcake | GIF | `src/assets/gift-whisk.jpg` | `terrific_bites.product_whisk-whimsy` | SKU: PROPOSED |
| `sprinkle-1` | `terrific_bites.product.sprinkle-1` | `TB-CUP-005` | `sprinkle-1` | Sprinkle Cupcakes | CUP | `src/assets/divine-1.jpg` | `terrific_bites.product_sprinkle-1` | SKU: PROPOSED |
| `sprinkle-2` | `terrific_bites.product.sprinkle-2` | `TB-CUP-006` | `sprinkle-2` | Cherry Sprinkle | CUP | `src/assets/divine-2.jpg` | `terrific_bites.product_sprinkle-2` | SKU: PROPOSED |
| `sprinkle-3` | `terrific_bites.product.sprinkle-3` | `TB-CUP-007` | `sprinkle-3` | Pink Whip | CUP | `src/assets/divine-3.jpg` | `terrific_bites.product_sprinkle-3` | SKU: PROPOSED |
| `sprinkle-4` | `terrific_bites.product.sprinkle-4` | `TB-CUP-008` | `sprinkle-4` | Confetti Whip | CUP | `src/assets/divine-4.jpg` | `terrific_bites.product_sprinkle-4` | SKU: PROPOSED |
| `choc-truffle` | `terrific_bites.product.choc-truffle` | `TB-CHO-001` | `choc-truffle` | Chocolate Truffle | CHO | `src/assets/choc-1.jpg` | `terrific_bites.product_choc-truffle` | SKU: PROPOSED |
| `choc-praline` | `terrific_bites.product.choc-praline` | `TB-CHO-002` | `choc-praline` | Hazelnut Praline | CHO | `src/assets/choc-2.jpg` | `terrific_bites.product_choc-praline` | SKU: PROPOSED |
| `choc-ganache` | `terrific_bites.product.choc-ganache` | `TB-CHO-003` | `choc-ganache` | Ganache Bites | CHO | `src/assets/choc-3.jpg` | `terrific_bites.product_choc-ganache` | SKU: PROPOSED |
| `choc-caramel` | `terrific_bites.product.choc-caramel` | `TB-CHO-004` | `choc-caramel` | Salted Caramel | CHO | `src/assets/choc-4.jpg` | `terrific_bites.product_choc-caramel` | SKU: PROPOSED |
| `choc-mint` | `terrific_bites.product.choc-mint` | `TB-CHO-005` | `choc-mint` | Mint Delight | CHO | `src/assets/choc-5.jpg` | `terrific_bites.product_choc-mint` | SKU: PROPOSED |
| `choc-orange` | `terrific_bites.product.choc-orange` | `TB-CHO-006` | `choc-orange` | Orange Zest | CHO | `src/assets/choc-6.jpg` | `terrific_bites.product_choc-orange` | SKU: PROPOSED |
| `choc-almond` | `terrific_bites.product.choc-almond` | `TB-CHO-007` | `choc-almond` | Roasted Almond | CHO | `src/assets/choc-7.jpg` | `terrific_bites.product_choc-almond` | SKU: PROPOSED |
| `choc-white` | `terrific_bites.product.choc-white` | `TB-CHO-008` | `choc-white` | White Dream | CHO | `src/assets/choc-8.jpg` | `terrific_bites.product_choc-white` | SKU: PROPOSED |
| `choc-berry` | `terrific_bites.product.choc-berry` | `TB-CHO-009` | `choc-berry` | Berry Truffle | CHO | `src/assets/choc-9.jpg` | `terrific_bites.product_choc-berry` | SKU: PROPOSED |
| `extra-donut` | `terrific_bites.product.extra-donut` | `TB-EXT-001` | `extra-donut` | Fanky Donut | EXT | `src/assets/extra-donut.jpg` | `terrific_bites.product_extra-donut` | SKU: PROPOSED |
| `extra-icecream` | `terrific_bites.product.extra-icecream` | `TB-EXT-002` | `extra-icecream` | Icecream Cone | EXT | `src/assets/extra-icecream.jpg` | `terrific_bites.product_extra-icecream` | SKU: PROPOSED |
| `extra-cheesecake` | `terrific_bites.product.extra-cheesecake` | `TB-EXT-003` | `extra-cheesecake` | Mini Cheesecake | EXT | `src/assets/extra-cheesecake.jpg` | `terrific_bites.product_extra-cheesecake` | SKU: PROPOSED |
| `extra-donuts-pair` | `terrific_bites.product.extra-donuts-pair` | `TB-EXT-004` | `extra-donuts-pair` | Donuts Pair | EXT | `src/assets/extra-donuts-pair.jpg` | `terrific_bites.product_extra-donuts-pair` | SKU: PROPOSED |

## Category rows (6/6)

| Slug | Category external key | Code (proposed) | Name (EN) | Proposed Odoo xml_id | Confirmation status |
|---|---|---|---|---|---|
| `cupcakes` | `terrific_bites.category.cupcakes` | CUP | Cupcakes | `terrific_bites.category_cupcakes` | Code: BUSINESS_CONFIRMATION_REQUIRED |
| `cakes` | `terrific_bites.category.cakes` | CAK | Cakes | `terrific_bites.category_cakes` | Code: BUSINESS_CONFIRMATION_REQUIRED |
| `chocolates` | `terrific_bites.category.chocolates` | CHO | Chocolates | `terrific_bites.category_chocolates` | Code: BUSINESS_CONFIRMATION_REQUIRED |
| `donuts` | `terrific_bites.category.donuts` | DON | Donuts | `terrific_bites.category_donuts` | Code: BUSINESS_CONFIRMATION_REQUIRED |
| `gifts` | `terrific_bites.category.gifts` | GIF | Gifts | `terrific_bites.category_gifts` | Code: BUSINESS_CONFIRMATION_REQUIRED |
| `extras` | `terrific_bites.category.extras` | EXT | Extras | `terrific_bites.category_extras` | Code: BUSINESS_CONFIRMATION_REQUIRED |

## Reading the "Confirmation status" column

Every row's `external_key`, `slug`, and proposed `xml_id` are **APPROVED** (D05/D06/D20 —
pure technical identifiers, safe to finalize now). Only the **SKU** (D04) and **category
code** (D03) columns remain open for explicit business sign-off, since those are the two
values with real commercial/operational weight (they become permanent references the
moment Odoo import runs). See [sku-approval-register.md](sku-approval-register.md) and
[category-approval-register.md](category-approval-register.md) for the dedicated sign-off
tables.
