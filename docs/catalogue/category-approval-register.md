# Category Approval Register

Phase 2B deliverable. Full sign-off table for all 6 category codes, resolving
[catalogue-decisions-required.md](catalogue-decisions-required.md) item 2 and
[catalogue-decisions.json](../../data/catalogue/catalogue-decisions.json) `D03`.

**Status: APPROVED for all 6 rows (Phase 6, 2026-07-29 — see
[catalogue-business-approvals.json#D03](../../data/catalogue/catalogue-business-approvals.json)).**
No value in [categories.json](../../data/catalogue/categories.json) was changed to produce
this table — the codes are approved exactly as Phase 2A generated them.

## Full table (6/6)

| # | Slug | Code (approved, unchanged from Phase 2A) | Name (EN) | Display order | Confirmation status |
|---|---|---|---|---|---|
| 1 | `cupcakes` | `CUP` | Cupcakes | 1 | APPROVED |
| 2 | `cakes` | `CAK` | Cakes | 2 | APPROVED |
| 3 | `chocolates` | `CHO` | Chocolates | 3 | APPROVED |
| 4 | `donuts` | `DON` | Donuts | 4 | APPROVED |
| 5 | `gifts` | `GIF` | Gifts | 5 | APPROVED |
| 6 | `extras` | `EXT` | Extras | 6 | APPROVED |

Uniqueness: all 6 codes and all 6 slugs are distinct (verified by
`backend/scripts/validate_catalogue.py`'s `duplicate_slug` check).

## Why these codes and not the illustrative examples in this phase's instructions

This phase's instructions gave `CAKE`/`CUP`/`CHOC`/`GIFT`/`COOKIE`/`CATER` as *example*
code shapes, not a literal set to match against (`COOKIE` and `CATER` don't correspond to
any of the actual 6 categories). Phase 2A had already generated `CUP`/`CAK`/`CHO`/`DON`/
`GIF`/`EXT`, consistently applied across all 26 product SKUs. Two options were weighed:

1. **Keep as-is** — zero rework, already short/stable/uppercase, already the SKU prefix
   for all 26 products.
2. **Expand to 4-5 letters** (`CAKE`/`CHOC`/`DONUT`/`GIFT`/`EXTRA`, `CUP` unchanged) for
   legibility — `GIF` reads identically to the image-file-format acronym, and
   `CAK`/`CHO`/`DON` are truncations that could be misread as abbreviated words or names.

**Recommendation: option 1, keep as-is.** No structural defect exists (this is a cosmetic
legibility preference, not a data error), and per the MVP principle to avoid unnecessary
rework, changing a value that already flows consistently through 26 SKUs isn't justified
without a business reason to do so. The legibility concern is recorded here rather than
acted on unilaterally — if the business prefers longer codes, this table (and the 26 SKUs
in [sku-approval-register.md](sku-approval-register.md)) can be regenerated together before
Odoo import at effectively zero cost, since nothing has been imported anywhere yet.

## Consequence of confirming as-is

Once approved, `categories.json`'s `code_requires_confirmation` flips to `false`
(`code_generated` remains `true` for provenance). These codes become permanent SKU
prefixes the moment Odoo import runs — changing them afterward would require re-issuing
every affected product's `default_code`, which the target Odoo instance may or may not
allow cleanly depending on whether orders/invoices already reference the old SKU.
