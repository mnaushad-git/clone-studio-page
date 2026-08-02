# Odoo Configuration Checklist

Phase 2B deliverable. Everything that must be verified or configured against a **real,
named target Odoo instance** before the catalogue import (`catalogue-migration-plan.md`
Step B) can run. As of Phase 2B, nothing here could be resolved from the codebase — no
Odoo client existed and no instance had been contacted.

**Phase 4 update:** a read-only Odoo client and verification CLI now exist
(`python -m app.scripts.verify_odoo_connection`, see
[docs/integrations/odoo-environment-verification.md](../integrations/odoo-environment-verification.md)).
Every item below that is an Odoo-side *fact* (version, currency, tax records, UoM
records, field availability, etc.) can now be answered by running that command
against a configured instance — see
[odoo-operations-runbook.md](../integrations/odoo-operations-runbook.md) for how to
point it at one. Items that are *business decisions* (category codes, SKUs, product
type classification, opening inventory) still require explicit business sign-off —
the tooling reports them as open, it doesn't resolve them.

**Phase 5 update:** the controlled catalogue importer (`import_odoo_catalogue`) is now
implemented and reads this checklist's still-open items (`D08` real tax record, `D19`
Inventory-module status) as blocking conditions on `--apply` — see
[docs/integrations/odoo-catalogue-import.md](../integrations/odoo-catalogue-import.md).
No Odoo-side configuration item below was changed by this phase; `account.tax` still
has zero records and Inventory is still not installed on `terrific_dev` as of this
writing.

## Prerequisite: choose a target instance

Every item below is meaningless until a specific Odoo instance (version, edition, hosting)
is identified. A local Odoo Community instance is available for connectivity/verification
testing during Phase 4 — whether it is also the eventual production/staging target is a
deployment decision (see [deployment-topology.md](../architecture/deployment-topology.md)),
separate from this checklist.

- [x] Confirm Odoo version (e.g. 17, 18) and edition (Community vs. Enterprise) — affects
      which of the items below are even available (e.g. Extra Product Media is Odoo 15+).
      `verify_odoo_connection`'s `server_version` check answers this directly once run.
      **Live-verified 2026-07-28: Odoo `19.0-20260720`, Community edition** (`web_enterprise`
      is not among the 104 installed modules; a genuinely usable Odoo 19 target instance is
      now available, at `terrific_dev`). Still a local dev instance, not yet confirmed as the
      production/staging target — that remains a separate deployment decision.
- [x] Confirm hosting model (Odoo.sh, self-hosted, on-premise) and how the FastAPI backend
      will authenticate to it (API key, OAuth, XML-RPC/JSON-RPC credentials). This phase's
      client supports JSON-RPC with password or API-key auth — see
      [odoo-client.md](../integrations/odoo-client.md) for the protocol decision.
      **Live-verified 2026-07-28: on-premise / self-hosted** (server file path evidence:
      `C:\Program Files\Odoo 19.0.20260720\server\...`, not an Odoo.sh/Odoo Online URL
      pattern). Currently authenticates via JSON-RPC + password; a real Odoo API key was
      not available to test API-key auth or the newer JSON-2 protocol — see
      [odoo-client.md](../integrations/odoo-client.md) §2a.

## Company / instance-wide settings

- [x] **Currency** (`D07`): confirm the instance's company currency is set to SAR. All 26
      catalogue prices assume this; no conversion logic exists or is planned.
      **Live-verified 2026-07-28: SAR** (res.company id=1, currency_id=151/SAR, single
      company). `D07` is fully closed out.
- [x] **Language**: confirm whether Arabic (`ar_001` or `ar_SA`) is installed and activated
      as an Odoo language. This determines whether Arabic product names/descriptions (once
      the `D13` content-completion project produces them) go into native Odoo translation
      fields or a custom field. Not needed for this phase's English-only import.
      **Live-verified 2026-07-28: `ar_001` is installed and active** (alongside `en_US`).
      The activation prerequisite for `D13` is satisfied — no actual Arabic translations
      exist yet, which remains `D13`'s separate, still-open content-completion question.
- [ ] **External-id module namespace**: confirm `terrific_bites` is an acceptable/available
      module name for `ir.model.data` external ids (per `D05`/`D20`), or that an existing
      module name should be reused instead.
      **Live-verified 2026-07-28: valid and conflict-free** — zero `ir.model.data` rows
      exist under `module="terrific_bites"` on this instance (see
      [odoo-external-key-strategy.md](../integrations/odoo-external-key-strategy.md)).
      Note a *different*, unrelated module (`terrific_bites_custom`) is already installed —
      see [catalogue-import-readiness.md](catalogue-import-readiness.md) — but its
      `ir.model.data` rows live under `module="terrific_bites_custom"`, so there is no
      namespace collision with the `terrific_bites` external-key strategy.

## Tax configuration (`D08`)

- [ ] Identify or create the `account.tax` record representing the current single 5% VAT
      rate (recommended logical label: `STANDARD_SALES_VAT`).
      **Live-verified 2026-07-28: no such record exists yet.** `account.tax` has **zero**
      records of any kind on this instance, despite `l10n_sa`/`l10n_gcc_invoice` (Saudi
      fiscal localization) being installed — the Fiscal Localization/chart-of-accounts setup
      wizard has not been run. Creating the tax record is a write operation, out of scope for
      this phase.
- [ ] Confirm whether the business intends per-category or per-product tax variation in the
      future (current recommendation: no — one rate for all 26 products, see `D08`).
- [ ] Confirm — separately, as a business decision, not an Odoo setting — whether
      `sales_price` should be entered into Odoo as tax-inclusive or tax-exclusive, once
      `D21` (the PDP-vs-checkout VAT contradiction) is resolved.
      Context only, not a resolution: this instance's `res.company.account_price_include`
      (Odoo's own default company accounting setting) is `tax_excluded`.

## Unit of measure (`D09`)

- [x] Identify the real `uom.uom` record id to use for "Unit"/"Each" (naming varies —
      e.g. "Units", "PCE" — by Odoo localization).
      **Live-verified 2026-07-28: `uom.uom` id=1, name=`"Units"`** (a base unit,
      `relative_factor=1.0`, not derived from another UoM). `D09` is now `APPROVED` in
      `data/catalogue/catalogue-decisions.json`.
- [x] Confirm no catering/bulk product needs a different UoM (current recommendation:
      none do, based on the audited 26-product catalogue).
      No change from the Phase 2B finding — nothing in this phase's live check contradicts it.

## Product type / inventory tracking (`D10`, `D19`)

- [ ] Confirm Consumable is an acceptable classification for all 26 products in the target
      instance's configuration (vs. requiring Stockable for accounting/valuation reasons
      specific to that instance).
      **Live-verified 2026-07-28: Consumable (`consu`) is currently the *only* physical-goods
      option** — `product.template.type`'s selection is exactly `['consu', 'service',
      'combo']`; "Storable" isn't offered because the Inventory app isn't installed (see
      next item). This strengthens but doesn't replace the still-required business
      sign-off.
- [ ] If any product later becomes Stockable, confirm which warehouse/location the
      corresponding `stock.quant` should be created against.
      **Live-verified 2026-07-28: moot for now** — the Inventory/stock app is not installed
      on this instance at all (`stock.quant`/`stock.warehouse` both report "Model not
      installed"; confirmed independently via `ir.module.module`). Installing it is a
      prerequisite ops action before this item can be answered.
- [ ] Confirm the opening-inventory policy for first import (`D19`: zero, existing Odoo
      quantity, or business-supplied figure) — this is a business decision that still needs
      an Odoo-side answer (which location/warehouse, if not zero).
      Same Inventory-app-not-installed caveat as above applies.

## Variants (`D11`)

- [ ] Confirm whether `buttercream-cake`'s Size (6"/9") × Flavor (Vanilla/Chocolate)
      attribute-driven variants each need their own `default_code` (SKU), or whether the
      template's SKU is sufficient with variants distinguished by attribute values alone.
- [ ] Confirm attribute creation mechanics (`product.attribute` / `product.attribute.value`)
      match the recommended Size/Flavor attribute names, or whether the instance already has
      conflicting attribute definitions to reuse instead.

## Images (`D12`)

- [ ] Confirm the target instance's Odoo version supports a multi-image gallery
      (`product.image`, Odoo 15+) for `buttercream-cake`'s 3 additional gallery thumbnails,
      or whether only the single `image_1920` primary image field is available.
- [ ] Confirm expected image format/size constraints (Odoo auto-derives smaller variants
      from `image_1920`, but very large source files may need pre-resizing — none of the 26
      current images exceed ~135KB, which should be well within any reasonable limit, but
      this has not been verified against a real instance).

## Idempotency / re-import safety

- [ ] Confirm the chosen external-id strategy (`terrific_bites.product_<slug>` /
      `terrific_bites.category_<slug>`, per `D20`) does not collide with any existing
      `ir.model.data` records already present in the target instance.

## What this checklist explicitly does not cover

Order/cart/checkout/payment sync configuration (sales order import, invoicing, accounting)
— out of catalogue scope, sequenced separately per
`docs/architecture/implementation-roadmap.md` steps 10+.
