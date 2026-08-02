# Integration Principles — Odoo

Defines the Odoo integration boundary (task 9) in detail: how the adapter is isolated, how
sync stays idempotent/retryable/auditable/observable (rule 17), and how each of the three
data flows (products, orders, order status) actually works.

## 1. The adapter boundary

`backend/app/integrations/odoo/` is the **only** code in the repository allowed to know
about Odoo's API shapes, authentication, or protocol.

```
integrations/odoo/
├── client.py          # transport: session/auth, request/retry/backoff, low-level calls
├── mappers.py          # Odoo record ⇄ internal DTO translation, both directions
├── product_adapter.py  # read-only: fetch product/price/availability, map to catalogue DTOs
├── order_adapter.py    # write: create sales order from an outbox payload; read: fetch
│                        #   order/fulfilment/invoice status
└── exceptions.py       # typed exceptions (OdooUnavailable, OdooValidationError, ...)
                         #   so callers can distinguish retryable vs. non-retryable failures
```

**Rule enforced here:** nothing outside `integrations/odoo/` imports an Odoo client
library, constructs an Odoo API call, or parses an Odoo response shape. Every other module
talks to `product_adapter`/`order_adapter` through their typed function signatures, which
return/accept internal DTOs, not Odoo's native records. This is what makes rule 16
("Odoo-specific logic must remain inside an isolated integration adapter") checkable —
e.g. via an import-linter rule (`grimp`/`import-linter`) run in CI, not just a convention.

**Protocol**: Odoo exposes external integration through XML-RPC/JSON-RPC (the standard
"External API," available on every edition) and, on newer versions, REST-ish
controllers/`base_rest`-style modules if installed. The adapter targets the standard
XML-RPC/JSON-RPC external API by default, since it requires no extra Odoo module and works
across editions — final choice depends on the actual Odoo version/edition in use, which is
an open question (see [implementation-roadmap.md](implementation-roadmap.md)). Whichever
is chosen, it is a **supported, documented Odoo API** (rule 10) — never a raw SQL
connection to Odoo's database (rule 11), and never scraping Odoo's web UI.

## 2. Product flow: Odoo → background worker → PostgreSQL

```
Celery Beat (schedule) → product_sync task
  → product_adapter.fetch_changed_products(since=checkpoint)
  → mappers.to_catalogue_dto(...)
  → catalogue.service.upsert_from_sync(dto)   # idempotent upsert by odoo_product_id
  → sync_checkpoint updated
  → sync_audit_log row written (count, duration, outcome)
```

- **Idempotent**: upsert keyed on `odoo_product_id` (and `odoo_variant_id` for variants),
  never a blind insert. Running the same sync twice produces the same end state.
- **Retryable**: task failure (network, Odoo timeout, validation) leaves `sync_checkpoint`
  unmoved, so the next scheduled/retried run picks up from the same point; Celery's
  built-in retry/backoff handles transient failures.
- **Auditable**: every run writes a `sync_audit_log` row (started_at, finished_at, records
  processed, records failed, error summary) regardless of outcome.
- **Observable**: task success/failure/duration/record-count are emitted as metrics/log
  lines (§[observability.md](observability.md)) so sync health is visible without reading
  logs by hand.
- Descriptive fields (name, description, category, images) sync on the slower schedule
  (07:00/14:00 Asia/Riyadh); price and availability sync more frequently, because they're
  more time-sensitive and cheaper to fetch incrementally — see
  [component-view.md](component-view.md) §4 for the full schedule table.
- The very first run of this flow has nothing to sync from, because the current product
  catalogue is a hardcoded frontend array that has never existed in Odoo — this is why
  **catalogue import into Odoo** is its own step before the sync worker is built (see
  [implementation-roadmap.md](implementation-roadmap.md) steps 4–6).

## 3. Order flow: PostgreSQL transactional outbox → background worker → Odoo

```
FastAPI: orders.service.create_order()
  → INSERT order (status=pending_sync), order_item rows, outbox_event row   [one transaction]
  → commit

Celery: order_export task (near-real-time trigger + periodic sweep safety net)
  → SELECT outbox_event WHERE status='pending' (locked/claimed, e.g. SELECT ... FOR UPDATE SKIP LOCKED)
  → order_adapter.create_sales_order(payload, idempotency_key=order.id)
  → on success: order.odoo_sale_order_id set, order.sync_status='synced',
                 outbox_event.status='sent'
  → on failure: outbox_event.status='failed', attempt_count incremented,
                 error recorded — picked up again by the retry/recovery task
```

- **Idempotent**: the outbox payload includes the internal order UUID as Odoo's
  `client_order_ref` (or equivalent custom field). Before creating a sales order, the
  adapter checks whether an Odoo order already carries that reference (covers the case
  where Odoo accepted the order but the confirmation response was lost). This is what
  prevents a retried export from creating a duplicate sales order.
- **Retryable**: `outbox_event.status='failed'` rows are exactly what the order
  retry/recovery task (every 5 min) sweeps and re-attempts, with capped backoff and a
  dead-letter state (`status='dead'` after N attempts) that surfaces to
  [observability.md](observability.md) rather than retrying forever.
- **Auditable**: `outbox_event` itself is the audit trail (payload, attempts, timestamps,
  last error) — never deleted, only transitioned.
- **Observable**: outbox queue depth and failure rate are the primary health metric for
  this flow (§[observability.md](observability.md)) — a growing `pending`/`failed` count
  is the signal something is wrong with Odoo reachability or data.
- This is exactly why rule 18 ("order creation and its outbox event must be committed in
  one PostgreSQL transaction") matters: without it, a crash between "save the order" and
  "queue the export" would silently strand orders that are never sent to Odoo.

## 4. Order-status flow: Odoo → background worker (or authenticated callback) → PostgreSQL

Two supported mechanisms, not mutually exclusive:

- **Polling worker (primary, always present)**: every 5 minutes, `order_status_import`
  task asks Odoo for status changes on orders with `sync_status='synced'` and
  `fulfilment_status` not yet terminal, and upserts `order.fulfilment_status`,
  `order.odoo_invoice_id`, and an `order_status_history` row per change (idempotent on
  `(order_id, status, odoo_status_timestamp)`).
- **Authenticated callback (optional, additive)**: if/when Odoo (via a webhook automation
  or a small custom module) can push a status change, FastAPI exposes a narrow
  `/api/v1/integrations/odoo/webhooks/order-status` endpoint, authenticated with a shared
  secret/HMAC signature, that does the same idempotent upsert. This is a **thin, isolated**
  route — it still writes through `orders.service`, not directly to the table — and it
  supplements rather than replaces the polling worker, since Odoo's ability to call
  outbound webhooks depends on the deployment (self-hosted vs. Odoo.sh) and is an open
  question (see [implementation-roadmap.md](implementation-roadmap.md)).
- Either way, this is still "background worker or authenticated callback," never a
  synchronous Odoo call inside a customer-facing request (rule 6/12) — a customer checking
  their order status reads PostgreSQL's last-synced value, not a live Odoo call.

## 5. Reconciliation

Reconciliation is a **read-only comparison**, not a repair mechanism:

- **Order reconciliation (hourly)**: for orders synced in the last N days, compare
  PostgreSQL's `fulfilment_status`/`sync_status` against a fresh Odoo read. Drift is
  written to `reconciliation_result` with enough detail (order id, field, expected vs.
  actual) for a human or a follow-up task to act on.
- **Product reconciliation (weekly)**: full diff of PostgreSQL's catalogue cache against
  Odoo's current product set — catches products deleted/deactivated in Odoo that a
  targeted incremental sync might miss, and catalogue entries that exist in PostgreSQL
  with no matching Odoo product (data integrity signal).
- Reconciliation **never silently auto-corrects** a conflict it finds beyond what the
  normal sync direction already does (Odoo → PostgreSQL for product/status fields) — it
  surfaces drift for review, consistent with Odoo being the authoritative source (rule 5)
  and PostgreSQL never being written to make Odoo agree with it.

## 6. Failure handling summary

| Failure | Handling |
|---|---|
| Odoo temporarily unreachable during scheduled sync | Task retries with backoff (Celery); `sync_checkpoint` unmoved; no partial/corrupt state written. |
| Odoo rejects an order (validation error — e.g., a product Odoo no longer has) | `outbox_event.status='failed'` with the Odoo error captured; **not** silently retried forever — surfaced via observability/dead-letter after N attempts for manual resolution, since blind retry won't fix a data problem. |
| Worker crashes mid-task | Idempotent upserts + checkpoint-not-advanced design (§2/§3) mean a re-run is safe; no distributed transaction needed. |
| Duplicate order-status event delivered twice (callback retried, or overlapping poll + callback) | Idempotent upsert on `(order_id, status, odoo_status_timestamp)` — second delivery is a no-op. |
| Odoo API contract changes (version upgrade) | Isolated to `mappers.py`/`client.py` inside the adapter — no other module changes. |
