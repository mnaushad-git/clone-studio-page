# Odoo Import Reconciliation

Describes `import_odoo_catalogue --reconcile`, the read-only post-import
verification step (step 22 of the import order in
[odoo-catalogue-import.md](odoo-catalogue-import.md)).

## What it does

`OdooCatalogueImportService.run_reconcile(run_id)`:

1. Loads the given `import_run_id` (or the most recent `APPLY` run, if none given)
   and every `SUCCEEDED` item with a non-null `odoo_record_id`.
2. Re-reads those exact records from Odoo (via the ordinary read-only `OdooClient`,
   grouped by model into batched `read()` calls — never `OdooWriteClient`, so this
   step is incapable of writing to Odoo even if the code were changed carelessly).
3. Diffs each record's current Odoo field values against the item's
   `proposed_values_json`/`written_values_json` — a mismatch means the field changed
   in Odoo since the import (or the import's write didn't actually take, which would
   itself be a bug worth knowing about).
4. Diffs the current PostgreSQL `odoo_category_id`/`odoo_product_template_id` mapping
   against the item's `odoo_record_id` — a mismatch means PostgreSQL's mapping and the
   import's own record disagree (e.g. a different run overwrote the mapping).
5. Produces a report; **never writes to Odoo, never writes to PostgreSQL** (the CLI
   wrapper explicitly `session.rollback()`s afterward, even though nothing meaningful
   would have been flushed).

## Report shape

Written to `data/odoo/catalogue-import-reconciliation-report.json`:

```json
{
  "generated_at": "...",
  "run_id": "...",
  "run_mode": "APPLY",
  "run_status": "SUCCEEDED",
  "items_checked": 33,
  "field_mismatches": [
    {"canonical_external_key": "...", "odoo_model": "...", "odoo_record_id": 123,
     "field": "list_price", "expected": 12.5, "actual": 15.0}
  ],
  "postgresql_mapping_mismatches": [
    {"canonical_external_key": "...", "entity_type": "PRODUCT_TEMPLATE",
     "postgresql_odoo_id": 45, "import_item_odoo_id": 46}
  ],
  "errors": [],
  "clean": false
}
```

`clean: true` only when there are zero field mismatches, zero PostgreSQL mapping
mismatches, and zero errors. CLI exit code mirrors `clean` (`0` clean, `1` mismatches
found).

## When to run it

- After every `--apply` run, before treating the import as done.
- Periodically, once a recurring sync exists (not this phase — see CLAUDE.md's
  explicit "Do not begin recurring synchronisation yet").
- Before trusting a `--dry-run` report's predictions for a subsequent `--apply` — a
  reconciliation of the *previous* successful apply is a sanity check that nothing has
  drifted in Odoo out-of-band since.
