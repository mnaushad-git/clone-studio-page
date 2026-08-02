# Odoo Catalogue Import (Phase 5)

Phase 5 deliverable. Builds the controlled, write-capable Odoo catalogue importer on
top of Phase 4's read-only client (`app/integrations/odoo/client.py`). This document
is the architectural overview; see the sibling docs in this folder for the approval
gate, idempotency, auditing, reconciliation, rollback, image handling, security, and
testing detail, and [odoo-import-runbook.md](odoo-import-runbook.md) for the
step-by-step operational sequence.

## Status

Import functionality is fully implemented and safe to run in `--validate`/`--plan`/
`--dry-run` mode today. **`--apply` is blocked** — `D03`, `D04`, `D08`, `D10`, `D19` in
[data/catalogue/catalogue-business-approvals.json](../../data/catalogue/catalogue-business-approvals.json)
are still `PROPOSED`. See [odoo-import-approval-gate.md](odoo-import-approval-gate.md).

Variant/attribute writes (below) are gated **independently** by `D20`, also still
`PROPOSED` — category/product-template creation can be approved and applied on its own
timeline without also blessing the newer, higher-risk attribute write surface.

## Write-path architecture

```
app/scripts/import_odoo_catalogue.py          (CLI: --validate/--plan/--dry-run/--apply/--reconcile)
    -> app/services/catalogue/odoo_import_service.py   (orchestration, one class backs every mode)
        -> app/services/catalogue/odoo_import_planning.py   (pure matching/planning, no writes)
        -> app/services/catalogue/approval_gate.py           (business approval evaluation)
        -> app/integrations/odoo/write_client.py              (the only class that writes to Odoo)
        -> app/repositories/integration/odoo_import_{run,item}_repository.py  (audit persistence)
        -> app/repositories/catalogue/*  (existing Phase 3 repositories — odoo_*_id mapping updates)
```

`OdooWriteClient` is a separate class from `OdooClient` (Phase 4's read-only client) —
it does not extend or loosen `READONLY_ALLOWED_METHODS`. See
[odoo-import-security.md](odoo-import-security.md) for its allowlist.

## Import order

Exactly the sequence below (`app/services/catalogue/odoo_import_service.py::run_apply`):

1. Validate configuration (`OdooConfig.from_settings`)
2. Verify Odoo connectivity (`OdooClient.get_server_version`/`authenticate`)
3. Verify authenticated company and currency (`MetadataRepository.get_companies`)
4. Verify Odoo environment fingerprint (`EnvironmentSnapshot.fingerprint`)
5. Validate canonical catalogue (`categories.json`/`products.json` load + parse)
6. Validate business approval file (`approval_gate.evaluate_approval_gate`)
7. Regenerate conflict report (matching pass — external key / stored id / name / SKU)
8. Regenerate import plan (`odoo_import_planning.plan_categories`/`plan_products`)
9. Validate zero unresolved conflicts (blocked items gate, unless `--allow-partial`)
10. Create import-run record (`odoo_catalogue_import_runs`, mode=APPLY, status=RUNNING)
11. Import categories (`product.category.create`, matched items adopted as-is)
12. Create category XML IDs (`ir.model.data.create`, `terrific_bites.category_<slug>`)
13. Import product templates (`product.template.create`, `categ_id` resolved from step 11)
14. Create product-template XML IDs (`terrific_bites.product_<slug>`)
15. Resolve automatically created default variants (read via the write client's
    authenticated session is not needed — Odoo auto-creates `product.product` on
    template create; `default_code` is set on the template create payload itself)
16. Apply variant SKU where required (`product.product.write`, only if the
    auto-created variant's `default_code` doesn't already match)
17. Import shared attributes (`product.attribute.create`, matched by name first — see
    Variant strategy below; gated by `D20`, independent of `D03/D04/D08/D10/D19`)
18. Import attribute values, scoped to their attribute (`product.attribute.value.create`)
19. Import per-product attribute lines and read back the resulting combination
    variants (`product.template.attribute.line.create`/`.write`, then
    `product.product`/`product.template.attribute.value` read-back — see Variant
    strategy below)
20. Apply combination-variant SKUs (`product.product.write` on each resolved combination)
21. Import primary product images (`product.template.write` on `image_1920`)
22. Import additional product.image gallery records (`product.image.create`)
23. Verify imported Odoo records (folded into the reconciliation step, or run
    `--reconcile` separately)
24. Save Odoo IDs into PostgreSQL catalogue records (`odoo_category_id`,
    `odoo_product_template_id`, `odoo_product_variant_id`, `odoo_attribute_id`,
    `odoo_attribute_value_id`, `last_synced_at`)
25. Mark import run complete (`SUCCEEDED`/`PARTIALLY_COMPLETED`/`FAILED`)
26. Produce reconciliation report (`--reconcile`, a separate, later invocation)

Not imported this phase (explicitly out of scope): moments, recipients, merchandising
flags, homepage sections, SEO fields, storefront display order, reviews, ratings, fake
stock, recommendations, product availability, or Arabic text when null.

## Entity → Odoo field mapping

See [odoo-catalogue-field-mapping.md](odoo-catalogue-field-mapping.md) (Phase 4,
verified) and [../catalogue/final-data-ownership.md](../catalogue/final-data-ownership.md)
for the authoritative Odoo-owned vs. PostgreSQL-owned split. Phase 5's concrete payload
construction lives in `odoo_import_planning.plan_categories`/`plan_products`:

| Canonical field | Odoo field | Model |
|---|---|---|
| `name_en` | `name` | `product.category` / `product.template` |
| `code`, `slug`, Arabic name/description, `display_order` | — (PostgreSQL only) | |
| `sku` | `default_code` | `product.template` |
| `category_external_key` → resolved `categ_id` | `categ_id` | `product.template` |
| `sales_price` | `list_price` | `product.template` |
| `description_en` | `description_sale` | `product.template` |
| D09 approved UoM id | `uom_id` | `product.template` |
| D10 approved type (`consu`) | `type` | `product.template` |
| `sellable` | `sale_ok` | `product.template` |
| `active` | `active` | both |
| D08 approved tax record | `taxes_id` | `product.template` (blocked until D08 is APPROVED) |

## Variant strategy

Only `buttercream-cake` has genuine variant data today (size × flavor). Odoo's native
`product.attribute` → `product.attribute.value` → `product.template.attribute.line`
model is used directly — full detail, including the exact Odoo API mechanics (why
there's no `product.product.create`, how the read-back combination match works, and
the `create_variant="always"` requirement) lives in
[odoo-catalogue-variant-model.md](odoo-catalogue-variant-model.md). Summary:

- **Attributes are shared master data.** `plan_attributes()` (`odoo_import_planning.py`)
  matches by exact name against live Odoo *before* ever creating one — "Flavor" is
  created once and reused across every product with a flavor axis, never recreated per
  product. A matched attribute whose `create_variant` isn't `"always"` is `BLOCKED`
  (`EXISTING_ATTRIBUTE_WRONG_CREATE_VARIANT_MODE`), never silently reinterpreted.
- **Variants are the Cartesian product of a product's attribute axes.**
  `plan_variants()` produces one `PRODUCT_VARIANT` plan item per combination (2 sizes ×
  2 flavors = 4, today) — `MATCH`/`CREATE`/`BLOCKED`, never `SKIP`.
- **A variant CREATE never calls `product.product.create` directly** (not on the write
  allowlist) — it ensures the referenced `product.template.attribute.line`s exist
  (`create`, or `write` to ADD a value via `(4, id)` if the line already exists — never
  REPLACE, so existing combinations in Odoo are never disturbed), then reads
  `product.product` back by `product_tmpl_id` and matches the row whose
  `product.template.attribute.value` combination exactly equals the plan item's.
- **`catalogue_product_attribute_values`** is the Postgres table carrying each
  variant's full per-axis identity — attribute code/name, value label, and the Odoo
  attribute/value ids (`odoo_attribute_id`, `odoo_attribute_value_id`). It is the single
  source of truth read by the storefront, checkout pricing, and order/admin display;
  there is no separate JSONB representation.
- **Never automated:** shrinking an attribute's `value_ids` (retiring a combination) —
  always `BLOCKED` (a human acts in Odoo directly), since Odoo may delete a
  `product.product` that already has stock/sale history. No `unlink`/archive on any
  attribute-family model is ever on the write allowlist.
- Gated by `D20` (independent of `D03/D04/D08/D10/D19`) — see Status above.

## CLI

```
python -m app.scripts.import_odoo_catalogue --validate
python -m app.scripts.import_odoo_catalogue --plan
python -m app.scripts.import_odoo_catalogue --dry-run
python -m app.scripts.import_odoo_catalogue --apply --confirm-import [--allow-partial]
python -m app.scripts.import_odoo_catalogue --reconcile [--run-id UUID]
python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id UUID
python -m app.scripts.check_catalogue_import_approvals
```

See [odoo-import-runbook.md](odoo-import-runbook.md) for the safe operational sequence.
