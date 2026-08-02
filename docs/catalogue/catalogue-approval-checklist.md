# Catalogue Approval Checklist

Phase 2B deliverable. A single actionable checklist grouped by who needs to act, derived
from [catalogue-decision-pack.md](catalogue-decision-pack.md) and
[data/catalogue/catalogue-decisions.json](../../data/catalogue/catalogue-decisions.json).
Check off each item as it is formally approved; nothing here is self-approving.

**Phase 5 note:** the subset of these decisions that actually gate an Odoo write
(`D03`, `D04`, `D08`, `D09`, `D10`, `D19`) now also has a machine-readable copy at
[data/catalogue/catalogue-business-approvals.json](../../data/catalogue/catalogue-business-approvals.json),
checked automatically by `python -m app.scripts.check_catalogue_import_approvals`
before `import_odoo_catalogue --apply` is allowed to run — see
[docs/integrations/odoo-import-approval-gate.md](../integrations/odoo-import-approval-gate.md).
Approving a decision here (this checklist) does not by itself unblock `--apply`; the
JSON file must be updated too — this checklist remains the human-readable record.

## Group 1 — Safe to accept as MVP defaults (no action required to proceed)

These are already `APPROVED` in `catalogue-decisions.json`. No further sign-off is needed
before PostgreSQL schema design or Odoo client scaffolding can reference them.

- [x] `D01` — Product count baseline = 26 (28 is obsolete)
- [x] `D02` — Category structure stays flat (6 categories, no hierarchy)
- [x] `D05` — External key convention (`terrific_bites.product.<slug>` / `.category.<slug>`)
- [x] `D06` — Product/category slugs (reuse existing frontend ids, unchanged)
- [x] `D07` — Currency = SAR for all 26, no conversion
- [x] `D11` — Variant scope (1 template + 1 default variant for 25/26; real variants only
      for `buttercream-cake`)
- [x] `D12` — Image handling (import existing files as-is, no move/rename/compress)
- [x] `D14` — Product recommendations strategy (same-category fallback)
- [x] `D17` — Admin `ProductOverride` field split (Odoo-owned vs. Admin-owned)
- [x] `D18` — Reviews/ratings (mock-only, out of catalogue scope)
- [x] `D20` — Identifier mapping / Odoo external-id strategy

## Group 2 — Requires your explicit business approval before Odoo import

Nothing below blocks PostgreSQL schema design or frontend integration work — only Odoo
import specifically waits on these (see
[catalogue-import-readiness.md](catalogue-import-readiness.md)).

- [ ] `D03` — Category codes: confirm keeping `CUP`/`CAK`/`CHO`/`DON`/`GIF`/`EXT` as final
      (or request the 4-5 letter alternative) — see
      [category-approval-register.md](category-approval-register.md)
- [ ] `D04` — All 26 SKUs and the generation convention — see
      [sku-approval-register.md](sku-approval-register.md)
- [ ] `D08` (business half) — Whether displayed prices are VAT-inclusive or VAT-exclusive
      (see `D21` below — this is the same underlying question)
- [ ] `D10` — Odoo product type classification (Consumable recommended) for all 26
- [ ] `D15` — Whether `is_bestseller` should exist at all, and if so how it's computed
- [ ] `D16` — Homepage rail redesign direction (wire existing config vs. redesign vs. fix
      the "What's New" bug) — needed before Frontend Cutover, not before catalogue readiness
- [ ] `D19` — Opening inventory quantity policy for first Odoo import
- [ ] `D21` — **Price VAT-inclusive vs. VAT-exclusive contradiction** (PDP says inclusive;
      checkout math says exclusive) — blocks future checkout/pricing work, not catalogue
      import
- [ ] `D22` — Awareness-only: "Donuts" category has just 1 of 26 products (no action
      required, informational)

## Group 3 — Requires access to the real Odoo environment (cannot be resolved from code)

- [ ] `D07` (Odoo-side half) — Confirm target Odoo instance's company currency is SAR
- [ ] `D08` (Odoo-side half) — Confirm/select the real `account.tax` record for
      `STANDARD_SALES_VAT`
- [ ] `D09` — Confirm the real `uom.uom` record id to use for "Unit"/"Each"
- [ ] `D11` (nuance) — Confirm whether `buttercream-cake`'s variants each need their own
      `default_code`, or share the template's
- [ ] `D12` (nuance) — Confirm Odoo version/edition supports an extra-images gallery field
      for `buttercream-cake`'s 3 additional thumbnails
- [ ] `D19` (Odoo-side half) — Confirm target instance's stock/inventory module
      configuration before creating any `stock.quant`

## Sign-off record

| Decision(s) | Approved by | Date | Notes |
|---|---|---|---|
| _(all Group 2/3 items pending)_ | | | |

Once every Group 2 and Group 3 item above is checked and recorded in this table, the
catalogue is ready for Odoo import per
[catalogue-import-readiness.md](catalogue-import-readiness.md).
