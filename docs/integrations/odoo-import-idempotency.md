# Odoo Import Idempotency

Describes why re-running `import_odoo_catalogue --apply` against unchanged canonical
data is safe and produces zero duplicate writes.

## Matching priority (category and product alike)

Implemented once, in `app/services/catalogue/odoo_import_planning.py`
(`plan_categories`/`plan_products`), and reused unchanged by `--plan`, `--dry-run`,
and `--apply` — the three modes can never disagree about what already exists:

1. **External XML ID** — `ir.model.data` search under `module="terrific_bites"`,
   `name="category_<slug>"`/`"product_<slug>"`. The strategy Phase 4 already
   documented ([odoo-external-key-strategy.md](odoo-external-key-strategy.md)); Phase
   5 is the first phase to actually create these XML IDs.
2. **PostgreSQL-stored Odoo id** — `catalogue_categories.odoo_category_id` /
   `catalogue_products.odoo_product_template_id`, checked before any Odoo call at all
   (`OdooCatalogueImportService._postgres_odoo_ids()`). A category/product already
   mapped from a prior successful run costs zero Odoo round-trips on the next run.
3. **Exact SKU match** (products only) / **exact unique name match** (both) —
   requires human review (`MATCH_REQUIRES_ADOPTION`), classified as `BLOCKED`, never
   silently adopted. Two or more name matches block the same way a single one does —
   ambiguity is never resolved by picking the first result.
4. **Otherwise `CREATE`.**

## What a second `--apply` run does differently

- Categories/products already matched (steps 1–2 above) are recorded as
  `planned_action="MATCH"` / `actual_action="MATCH"`, not re-created. If a matched
  record's canonical values differ from what's currently in Odoo (only possible today
  for a MATCH found via XML ID or stored id — the importer reads the current Odoo
  values and diffs against `proposed_values`; see `_apply_category_item`/
  `_apply_product_item` in `odoo_import_service.py`), only the changed fields are
  written (`product.category.write`/`product.template.write`); an unchanged match is a
  true no-op — nothing is written, `written_values_json` stays null on that item.
- Images are matched by a synthetic `canonical_external_key`
  (`<product_key>.image.<role>.<display_order>`) looked up in
  `odoo_catalogue_import_items` across **all** prior runs
  (`OdooImportItemRepository.find_latest_by_external_key_across_runs`) before any
  upload is attempted — an image already successfully imported in a previous run is
  never re-uploaded.
- XML IDs are only created once per `(model, xml_id_name)` — a prior run's XML-ID
  create is itself an audited `EXTERNAL_XML_ID` item; a category/product matched by
  XML ID on this run has no reason to create a second one.

## Recovery from a failed Postgres commit after a successful Odoo write

Odoo and PostgreSQL cannot share a transaction. If an Odoo `create` succeeds but the
subsequent PostgreSQL flush/commit fails (process crash, connection loss), the
created Odoo record is **not** re-created blindly on retry: the very next run's
matching pass (step 1/2 above) finds it by XML ID before attempting another create.
This is the `ODOO_WRITE_SUCCEEDED_POSTGRES_PENDING` recovery path named in CLAUDE.md
Phase 5 §13, implemented via re-matching rather than a two-phase-commit protocol
PostgreSQL/Odoo can't actually support.

## Checksums

Every `odoo_catalogue_import_runs` row records three independent checksums:

- `source_checksum` — SHA-256 over `categories.json` + `products.json` only (not the
  merchandising/moments/recipients files, which never feed Odoo writes). Changes only
  when the canonical catalogue itself changes.
- `approval_checksum` — SHA-256 over every blocking approval decision's
  `(decision_id, status, approved_value)`. Changes if a business decision is
  approved/rejected/edited between plan generation and apply.
- `import_plan_checksum` — SHA-256 over every planned item's
  `(entity_type, canonical_external_key, planned_action)`. Changes if matching
  results differ (e.g. something was created in Odoo out-of-band between plan and
  apply).

`--apply` recomputes all three fresh at apply time — it does not trust a checksum
computed by an earlier `--plan` invocation, so there is no way to "replay" a stale
plan against a changed environment.
