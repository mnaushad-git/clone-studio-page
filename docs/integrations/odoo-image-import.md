# Odoo Image Import

Describes how the 29 verified catalogue images (26 primary + 3 additional gallery
images across the 26 products — see
[../catalogue/image-inventory.md](../catalogue/image-inventory.md)) are imported.

## Primary image

Written directly onto the created/matched `product.template` record's `image_1920`
field via `product.template.write` (`WRITE_ALLOWED_OPERATIONS` includes
`("product.template", "write")` — no separate model needed for the primary image).

## Gallery images

Written as `product.image` records (`product.image.create`), each with
`product_tmpl_id` pointing at the owning template, a synthetic `name`
(`<slug>-<display_order>`), and `image_1920` set to the encoded file content.
Display ordering is preserved via `display_order` in the item's audit metadata (Odoo's
own `product.image` model does not require a specific field name for this — the
canonical `display_order` from `products.json`'s `additional_images[]` array order is
what's preserved).

## Idempotency

Before uploading any image, the importer checks whether a prior run already succeeded
for the same synthetic external key
(`<product_external_key>.image.<role>.<display_order>`, e.g.
`product.swiss-frosting.image.primary.0`) via
`OdooImportItemRepository.find_latest_by_external_key_across_runs` — never re-uploads
an image that's already been imported, across any number of re-runs.

## What is read from disk

`app/services/catalogue/odoo_import_service.py::encode_image_base64(original_path)`
resolves `original_path` (as recorded in `products.json`) relative to the repository
root, reads the file, and base64-encodes it. Returns `None` — never raises — if the
file can't be found; the caller records that as a `FAILED` item
(`error_code="IMAGE_FILE_NOT_FOUND"`) rather than crashing the whole apply run.

**Original frontend image files are never renamed or modified** — this function only
reads them.

## What is never logged or persisted

Base64-encoded image content is:

- Never passed to `encode_image_base64()` during `--dry-run` (dry-run's proposed
  payloads for images only ever contain `role`/`display_order`/`checksum`/
  `source_path` — the actual bytes are never touched until a confirmed `--apply`).
- Never included in a structured log line (`OdooWriteClient`'s `odoo_write_attempt`/
  `odoo_write_succeeded` logs include `entity_type`/`canonical_external_key`/
  `planned_operation`, never the write's `values` payload).
- Never included in `odoo_catalogue_import_items.written_values_json` for an image —
  that column stores `{"role", "display_order", "checksum", "source_path",
  "image_payload": "EXCLUDED_FROM_AUDIT_LOG"}`, a literal marker instead of the bytes.
- Never included in any `data/odoo/*.json` report (dry-run report, execution plan,
  reconciliation report) — every report generator excludes image payloads by
  construction (they're never in the data structures being serialized in the first
  place, not filtered out after the fact).

## Checksum

`products.json`'s `primary_image`/`additional_images[].checksum` (already populated
by Phase 2A tooling) is preserved end-to-end in the audit item's `written_values_json`
— a future recurring sync can compare this checksum against a freshly-computed one to
detect a changed source image without re-reading Odoo.
