# Odoo Import Security (Phase 5 write boundary)

Describes `app/integrations/odoo/write_client.py::OdooWriteClient` — the only class in
this repository permitted to call `create`/`write` against Odoo. Phase 4's read-only
`OdooClient` (`app/integrations/odoo/client.py`) is untouched by this phase: its
`READONLY_ALLOWED_METHODS` allowlist still rejects every write-oriented method, and
every existing caller (repositories, discovery, `verify_odoo_connection`,
`plan_odoo_catalogue_import`) is unaffected.

## Three independent gates, all required

`OdooWriteClient._enforce_gates()` checks, in order, before any network call:

1. **`(model, method)` is in `WRITE_ALLOWED_OPERATIONS`** — a closed allowlist, not a
   blocklist:

   | Model | Methods |
   |---|---|
   | `product.category` | `create`, `write` |
   | `product.template` | `create`, `write` |
   | `product.product` | `write` (never `create` — Odoo auto-creates the default variant) |
   | `product.image` | `create`, `write` |
   | `ir.model.data` | `create` only (pins the `terrific_bites.*` XML ID after a category/template create) |

   Nothing else is reachable through this client — **not because of a runtime check
   on those specific models**, but because they never appear in the allowlist at all.
   `unlink`, `copy`, `copy_data`, `action_archive`, `action_unarchive` are additionally
   named in `EXPLICITLY_FORBIDDEN_METHODS` so a test can assert each one individually
   raises, independent of what else is or isn't allowlisted.

   Explicitly and permanently out of reach this phase: `stock.*` (no stock writes),
   `account.tax.create` (no tax creation), `uom.uom.create` (no UoM creation),
   `product.pricelist.create` (no pricelist creation), `res.company` writes (no
   company configuration changes), `ir.module.module.*` (no module installation),
   `res.users`/`ir.model.access` writes (no user or access-right changes),
   `product.attribute`/`product.attribute.value`/`product.template.attribute.line`
   (no attribute/variant modelling — see
   [odoo-catalogue-import.md#variant-strategy](odoo-catalogue-import.md)).

2. **`context.mode == "APPLY"`** — an `OdooWriteClient` can be constructed and even
   have `.create()`/`.write()` called on it during `--validate`/`--plan`/`--dry-run`/
   `--rollback-plan` (the service layer reuses the same class across modes for a
   single code path), but every call raises `OdooWriteNotAllowedError` unless the
   execution context's `mode` is `APPLY`. No Odoo write is reachable from any mode but
   a confirmed `--apply` run.

3. **A `WriteAudit` is mandatory, not optional** — every `create()`/`write()` call
   requires `entity_type`, `canonical_external_key`, and `planned_operation`; an
   `UPDATE` additionally requires a non-null `before_state` snapshot (updates must be
   recoverable — enforced at the gate, not left to caller discipline).

## Traceability

Every write call is logged (`app.integrations.odoo.write_client` logger,
`odoo_write_attempt`/`odoo_write_succeeded`/exception log on failure) with
`correlation_id`, `import_run_id`, `initiated_by`, `model`, `method`, `entity_type`,
`canonical_external_key`, `planned_operation` — never the actual field values (which
may include base64 image payloads; see [odoo-image-import.md](odoo-image-import.md)).
The service layer (`odoo_import_service.py`) separately persists the same information
plus before/after state into `odoo_catalogue_import_items` — see
[odoo-import-auditing.md](odoo-import-auditing.md).

## Writes are never blindly retried

`OdooWriteClient` calls `transport.call(..., retryable=False, ...)` — unlike the
read-only client's `execute_readonly` (which retries on connection/timeout/rate-limit
errors), a write is never automatically retried, since a failed create could have
partially succeeded server-side and retrying risks a duplicate. Recovery from a
mid-write failure is handled by re-matching on the next run (external key / stored
Postgres id / SKU), not by a transport-level retry — see
[odoo-import-idempotency.md](odoo-import-idempotency.md).

## Secrets

No secret (Odoo password/API key, session id) is ever included in a `WriteAudit`,
a log line, or a persisted `odoo_catalogue_import_items` row — the same redaction
discipline as Phase 4's `OdooIntegrationError.safe_context()` and
`OdooConfig.masked_dict()` applies unchanged; this phase adds no new place a secret
could leak. `data/odoo/*.json` reports never contain base64 image content, passwords,
API keys, cookies, or authentication headers — see
[odoo-catalogue-import-readiness.md](../catalogue/catalogue-import-readiness.md) and
[odoo-image-import.md](odoo-image-import.md).
