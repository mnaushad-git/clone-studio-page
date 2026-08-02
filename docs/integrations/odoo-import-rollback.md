# Odoo Import Rollback

Describes `plan_odoo_catalogue_rollback` and the manual recovery procedures for each
classification it produces. **This phase implements rollback *planning* only — no
automatic archive, restore, or delete exists anywhere in this codebase.** Destructive
deletes are unsafe by nature (an Odoo record created by an import may already have
been referenced elsewhere — a sales order line, a pricelist item); this doc and the
planner exist so a human can execute a rollback deliberately and correctly, not so a
script can do it unattended.

## Running it

```
python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id <uuid>
```

Read-only against PostgreSQL (`odoo_catalogue_import_runs`/`odoo_catalogue_import_items`
for the given run), never calls Odoo, never deletes/archives anything, never persists
anything (the CLI explicitly rolls back its own session). Writes
`data/odoo/catalogue-import-rollback-plan.json`.

## Classifications

| Classification | Meaning | Manual recovery |
|---|---|---|
| `SAFE_TO_ARCHIVE` | A category/product this run **created**. | In Odoo, set `active = False` on the record (`product.category`/`product.template` id from the item's `odoo_record_id`). Do not delete — other data may reference it. |
| `SAFE_TO_RESTORE` | A category/product this run **updated** an existing (matched) record's fields on. | Write the item's `before_state_json` values back onto `odoo_record_id` via Odoo's own UI or `write()` — the pre-import values are preserved verbatim. |
| `MANUAL_REVIEW_REQUIRED` | An image this run created — Odoo has no clean "archive" semantics for `product.image`/`image_1920`. | Review the record (`odoo_model`/`odoo_record_id`) in Odoo directly and remove/blank it manually if rollback is genuinely required. |
| `NOT_ROLLBACKABLE` | An `ir.model.data` (XML ID) row this run created. | Not deleted automatically. If a full rollback is genuinely required: delete the specific `ir.model.data` row (`module="terrific_bites"`, `name=<xml_id_name>`) directly in Odoo — **only** after the record it points to has itself been archived/restored, so a stale XML ID never points at nothing. |
| `NO_ACTION_REQUIRED` | Item was `MATCH` (nothing created/changed), `BLOCKED`, `SKIPPED`, or `FAILED`. | Nothing to roll back — no Odoo write happened for this item. |

## Why archive, never delete

Odoo records participate in referential relationships this importer has no visibility
into (a `product.template` a sales order already references, a `product.category` a
pricelist rule already filters on). Deleting risks breaking those; archiving
(`active = False`) removes the record from normal Odoo views/searches without breaking
anything that already points to it. This is a deliberate, permanent policy for this
importer, not a temporary limitation.

## Example workflow

```
python -m app.scripts.import_odoo_catalogue --apply --confirm-import
# ... later, if something needs undoing ...
python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id <the run's id>
# Read data/odoo/catalogue-import-rollback-plan.json
# Execute each SAFE_TO_ARCHIVE/SAFE_TO_RESTORE/MANUAL_REVIEW_REQUIRED item manually in Odoo
# Once done, if PostgreSQL's odoo_*_id mapping should also be cleared, do so directly
#   (no script performs this automatically — it's an explicit, reviewed action)
```
