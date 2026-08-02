# Catalogue Import Readiness

Phase 2B deliverable, updated after Phase 4 (Odoo Environment Verification) and Phase
4B (Live Odoo Environment Verification, 2026-07-28). States, plainly, what is and
isn't ready to start next, and why — cross-referencing
[catalogue-decision-pack.md](catalogue-decision-pack.md) and
[catalogue-migration-plan.md](catalogue-migration-plan.md). This document does not
start any of the work it describes.

## Critical Phase 4B finding: an Odoo-side custom module already implements part of the merchandising domain

This is the single most important discovery of Phase 4B and needs explicit
business/architecture review before further Odoo integration work proceeds — it is
**not resolved here**, only documented with live evidence.

The `terrific_dev` target instance has a custom module already installed:
`terrific_bites_custom` (version `19.0.1.0.0`, author "Terrific Bites"). Its own
module description, read directly from `ir.module.module.summary`:

> "Custom fields, models and API endpoints backing the Terrific Bites React portal
> (BRSD_Terrific Bites V1.0.1). Adds what the standard Website/Sales/Loyalty apps
> don't cover: storage/ingredients/allergens tabs, gift-card inscriptions,
> configurable landing-page sections, and delivery-partner pricing rules."

It defines 8 custom fields on `product.template`/`product.product` (see
[odoo-catalogue-field-mapping.md](../integrations/odoo-catalogue-field-mapping.md)),
plus these custom models — verified live, with real record counts:

| Model | Records | What it looks like |
|---|---|---|
| `terrific.home.section` | 6 | **Exact match to this repo's real homepage rail structure.** Rows: `our_products` ("Our Products", `product_grid`), `gifts_for_every_moment` ("Gifts for Every Moment", `circle_grid`), `divine_treats` ("Divine Treats and Indulgent Desserts", `carousel`), `whats_new` ("What's New", `product_grid`), `event_catering` ("Event Catering & Customized Gifting", `promo_split`), `cupcake_perfection` ("Cupcake Perfection: Love-Baked by Terrific Bites", `editorial`). These are the same rail names/positions this repo's own audit describes for the real (hardcoded) storefront homepage — including `whats_new`, the exact rail `D16` documents as buggy (duplicates the "Products" rail instead of filtering to `isNew`). |
| `terrific.home.section.item` | 14 | Per-section items (`section_id`, `item_type`, `product_id`/`category_id`, image, link, `start_date`/`end_date`) — a working content-scheduling model for rail contents. |
| `terrific.storefront.settings` | 1 | Singleton settings row, including `bought_earlier_title`/`bought_earlier_max_items`/`bought_earlier_lookback_days`/`bought_earlier_eligible_states` — i.e. a "Bought Earlier" personalized rail, a concept that doesn't exist anywhere in this repo's current catalogue/merchandising schema or decision pack. |
| `terrific.hero.slide` | 1 | Homepage hero carousel slide (title, CTA, desktop/mobile images, scheduling). |
| `terrific.storefront.announcement` | 1 | Site-wide announcement banner (message, CTA, scheduling). |
| `terrific.loyalty.settings` | 0 | Loyalty-points program config (`points_per_currency_spent`, `currency_value_per_point`, `free_delivery_threshold`) — ties to the `x_loyalty_points` product field. Not yet configured (0 rows) but the model exists. |
| `terrific.delivery.partner` | 0 | Delivery-partner pricing rules (`coverage_area`, `pricing_rule_type`, `base_price`). Not yet configured. |
| `terrific.inscription.color` | 0 | Cake-inscription color options, referenced by `x_inscription_color_ids`. Not yet configured. |

### Why this matters

CLAUDE.md rule 9 and [data-ownership.md](../architecture/data-ownership.md) establish
that Odoo owns ERP/commercial data only, while PostgreSQL/Admin Portal owns *all*
storefront merchandising — homepage sections, badges, display order, and (per `D16`'s
still-open status) the homepage-rail redesign specifically. This custom module
already implements homepage sections, a hero carousel, a site announcement banner,
and a "Bought Earlier" rail concept **inside Odoo**, with 23 real rows of content
already entered — populated by someone, for some purpose, before this verification
phase ran. This directly overlaps the domain `D16` describes as still open and
unapproved, and it does so via a mechanism (a bespoke Odoo module named
`terrific_bites_custom`, referencing "the Terrific Bites React portal
(BRSD_Terrific Bites V1.0.1)") that isn't mentioned anywhere in this repo's
architecture docs.

**This phase does not know, and did not investigate further:**
- Whether `terrific_bites_custom` is this same project's own prior/parallel work
  (e.g. built by a different vendor/team under a different codename, "BRSD"), an
  abandoned prototype, or something unrelated that happens to share the product's name.
- Whether the target architecture (`docs/architecture/target-architecture.md`) should
  be revised to source homepage-section content from Odoo via this module instead of
  (or alongside) the planned PostgreSQL `storefront`/`section_product` tables that
  already exist in this repo's own SQLAlchemy models (`app/models/storefront/`).
- Whether `D16` should be resolved by "wire the existing config to the real
  homepage" (its option 1) using *this* Odoo module as the source of truth, which
  would be a materially different answer than anything currently documented.

None of this was decided or acted on in this read-only phase — it is recorded here,
prominently, as the top item for business/architecture review before the next phase
of Odoo integration work (or any `D16` resolution) proceeds. See also
[odoo-external-key-strategy.md](../integrations/odoo-external-key-strategy.md) for
confirmation that this module's `ir.model.data` namespace (`terrific_bites_custom`)
does not collide with this repo's own external-key namespace (`terrific_bites`) —
they are two distinct module names, which is itself a sign these were built
independently rather than as the same integration effort.

### Also found, lower-severity (environment hygiene, not a conflict)

The `terrific_dev` instance is not empty: 23 pre-existing `product.template` records
exist — 3 standard Odoo/eCommerce demo records ("Gift Card", "Top-up eWallet",
"Standard delivery") and 20 generic bakery placeholder products ("Classic Red Velvet
Cake", "Vanilla Bean Cupcake", "Chocolate Chip Cookie", etc., all uncategorized —
`categ_id` unset). **None of these conflict with any of the 26 canonical Terrific
Bites products** by name, SKU, or external key — confirmed both by
`plan_odoo_catalogue_import`'s exact-match search (all 32 `existing_match` fields are
`null`) and by manual review of every one of the 23 records. `product.category` also
has only the 4 stock Odoo defaults (`Deliveries`, `Expenses`, `Goods`, `Services`) —
none of the 6 proposed Terrific Bites categories exist yet. Recommendation: clean up
or clearly exclude this placeholder data before any real import, as an operational
housekeeping step — not a blocker for continuing verification/planning work.

## Readiness by downstream step

| Step | Ready to start? | Blocked by |
|---|---|---|
| **PostgreSQL schema design** (Alembic migrations, SQLAlchemy models) | **Done** (Phase 3). | Nothing. |
| **Odoo API client implementation** (`app/integrations/odoo/`) | **Done** (Phase 4) — read-only client, environment verification, catalogue-mapping evidence gathering, dry-run import planner. See [docs/integrations/](../integrations/). | Not blocked. |
| **Odoo catalogue import** (creating real `product.category`/`product.template` records) | **Implemented, blocked on approval** (Phase 5) — the full controlled importer (`import_odoo_catalogue --validate/--plan/--dry-run/--apply/--reconcile`, write-capable client, PostgreSQL audit tables, rollback planning) exists and is tested in `--validate`/`--plan`/`--dry-run` mode. See [docs/integrations/odoo-catalogue-import.md](../integrations/odoo-catalogue-import.md). | `D03`, `D04`, `D08`, `D10`, `D19` in [data/catalogue/catalogue-business-approvals.json](../../data/catalogue/catalogue-business-approvals.json) (`D09` is already `APPROVED`) — `python -m app.scripts.check_catalogue_import_approvals` confirms this live: `--apply` is refused until all five are `APPROVED` with a real value. |
| **Frontend cutover** (Storefront/Admin switching from `products.ts` to a real API) | **No** (not in scope yet — no API exists) | The FastAPI catalogue endpoint itself doesn't exist; also needs `D16`'s homepage-rail direction decided first. |

## Phase 4 update

A read-only Odoo integration client, environment-verification CLI
(`verify_odoo_connection`), and dry-run import planner (`plan_odoo_catalogue_import`)
are now implemented and tested (81 mocked unit tests, zero live-Odoo dependency for
normal CI). This resolves the "Odoo API client implementation" row above from
**Partially** to **Done** — but does **not** change the Odoo-import row: the six
open decisions (`D03`/`D04`/`D08`/`D09`/`D10`/`D19`) are business/Odoo-configuration
facts, not implementation work, and remain exactly as open as Phase 2B left them. See
[odoo-configuration-checklist.md](odoo-configuration-checklist.md) for how the
verification tooling now answers (or will answer, once pointed at a named target
instance) the Odoo-side half of those items.

## Why PostgreSQL schema design is not blocked by any open decision

This is the most important and possibly counter-intuitive finding of this phase: **none of
the 22 decisions in the decision pack block starting PostgreSQL schema design.**

The reasoning is structural, not optimistic: every open decision (SKU values, category
codes, tax mapping, UoM, product type, opening inventory) is a *value* that will populate a
*column*, not a column that doesn't yet have a defined shape. `postgresql-field-mapping-draft.md`
already specifies the `product` / `product_variant` / `product_merchandising` / `moment` /
`recipient` table shapes precisely enough to write real Alembic migrations today:

- `product.sku` can be a `VARCHAR` column today even though the actual SKU values are
  `PROPOSED` — the column doesn't care what string eventually lives in it.
- `product.tax_class` / `product_price_cache` can exist as designed even though the real
  Odoo tax id is `ODOO_VERIFICATION_REQUIRED` — it's a synced cache column, populated by a
  worker that doesn't exist yet either.
- `product.category_id` as a flat FK (no self-reference needed) is settled by `D02`.

In other words: the *shape* of the catalogue schema is fully determined by
`docs/architecture/data-ownership.md` and `postgresql-field-mapping-draft.md`, both of
which predate this phase and are architecture-approved. What remains open is business data
that fills cells, not table/column design. This phase's instructions explicitly say not to
create the SQLAlchemy models yet, so this phase does not do so — but nothing found here
would need to change that design once it does start.

## Why frontend integration is not blocked by any catalogue decision either

Same logic: the Storefront/Admin UI is explicitly frozen (not to be redesigned) and the
future FastAPI catalogue endpoint's contract can be designed against the schema above
regardless of which SKUs/tax classes/UoMs end up confirmed. What *does* block frontend
cutover is that the FastAPI service, the Postgres tables, and the product-sync worker
don't exist yet — none of which this phase creates, per its explicit scope limits — plus
the still-open `D16` decision on homepage-rail behavior (preserve the existing bug
byte-for-byte, or correct it as part of the cutover — a decision that must be made
explicitly, not defaulted).

## Why Odoo import specifically is blocked

Odoo import is the one step where open decisions have real teeth, because SKUs, category
codes, tax records, and UoM records become **permanent** the moment `ir.model.data`
external-ids are created and orders/invoices start referencing them. The full list:

- `D03` — category codes (cascades into all 26 SKUs)
- `D04` — the 26 SKUs themselves
- `D08` — real Odoo tax record + business confirmation on VAT treatment
- `D09` — real Odoo UoM record
- `D10` — product type classification (Consumable/Stockable/Service)
- `D19` — opening inventory policy

None of these can be resolved without either (a) explicit business sign-off (recorded via
[catalogue-approval-checklist.md](catalogue-approval-checklist.md)) or (b) access to a real,
named target Odoo instance (recorded via
[odoo-configuration-checklist.md](odoo-configuration-checklist.md)). Both are outside this
phase's scope to obtain.

## Remaining blockers, summarized

1. Business sign-off on category codes, SKUs, product type classification, `is_bestseller`
   scope, homepage-rail direction, opening inventory policy, and the VAT-inclusive/exclusive
   contradiction (`D21`).
2. Access to a real, named target Odoo instance to verify: company currency, the real tax
   record, the real UoM record, variant SKU behavior, and image-gallery field availability.
3. Neither of the above exists yet — this phase does not select or provision an Odoo
   instance, per its explicit scope limits.

## Phase 5 update

The controlled Odoo catalogue importer described above is now implemented in full
(business approval gate, write-capable client with a closed model/method allowlist,
PostgreSQL import-run/item audit tables, idempotent matching, image import, rollback
planning). This resolves the "Odoo catalogue import" row from **No** to **Implemented,
blocked on approval** — the remaining blocker is exactly the same business sign-off
this document already named (`D03`/`D04`/`D08`/`D10`/`D19`), now tracked in a
machine-readable, human-editable-only approval file rather than only in prose. No
Odoo write has occurred anywhere against any instance during this phase — see
[docs/integrations/odoo-import-approval-gate.md](../integrations/odoo-import-approval-gate.md).

## What this phase recommends as the next phase

Given the above, the recommended Phase 3 is **not** "start the Odoo import" — it is:

1. Circulate [catalogue-approval-checklist.md](catalogue-approval-checklist.md) Group 2
   items to the business for sign-off.
2. In parallel (no dependency), begin **PostgreSQL schema design** (Alembic migrations +
   SQLAlchemy models for `catalogue`/`merchandising`/`content` domains per
   `data-ownership.md`), since nothing here blocks it.
3. Identify and gain access to a real target Odoo instance to resolve the Group 3 items in
   [odoo-configuration-checklist.md](odoo-configuration-checklist.md).
4. Only once both (1) and (3) are resolved, proceed to the actual Odoo catalogue import
   (`catalogue-migration-plan.md` Step B).

## What this phase (Phase 5) recommends as the next phase

Steps 1–3 above are exactly the work carried out since (Phases 3/4/4B and this
phase's own approval-gate scaffolding); step 4 (the actual Odoo catalogue import) is
now implementation-complete and gated purely on business sign-off. The recommended
next phase is therefore:

1. Obtain explicit business sign-off on `D03`/`D04`/`D08`/`D10`/`D19`, recorded
   directly in [data/catalogue/catalogue-business-approvals.json](../../data/catalogue/catalogue-business-approvals.json).
2. Resolve D08's Odoo-side prerequisite independently of the business question:
   configure at least one `account.tax` record on the target instance (currently
   zero exist — see [docs/integrations/odoo-import-approval-gate.md](../integrations/odoo-import-approval-gate.md)).
3. Review a fresh `--dry-run` report against the target instance per
   [docs/integrations/odoo-import-runbook.md](../integrations/odoo-import-runbook.md).
4. Only then run `--apply`, with explicit, separate confirmation per the runbook's
   human review gate.
5. Investigate and resolve the `terrific_bites_custom` module overlap (see above)
   before any merchandising/homepage-section data is ever synced from Odoo — Phase 5
   deliberately does not import merchandising/homepage data, so this remains open.
6. Only after a successful, reconciled `--apply`: begin designing the catalogue
   FastAPI endpoints and the recurring Odoo→PostgreSQL sync worker — both explicitly
   out of scope for Phase 5.
