# Observability

Defines the logging, audit, and correlation-ID approach (task 14) and how rule 17's
"observable" requirement is satisfied concretely for product/order sync.

## 1. Correlation IDs

- Every inbound HTTP request gets a correlation id: read from an incoming
  `X-Correlation-ID` header if present (useful for tests/tooling), otherwise generated
  (`req_<uuid>`) by a FastAPI middleware at the edge.
- The id is: attached to the structured log context for the lifetime of the request,
  returned in the error envelope (`error.correlation_id`, per
  [api-standards.md](api-standards.md)) so a user-reported error is traceable in one step,
  and propagated to any downstream call the request triggers synchronously (there should
  be very few — rule 6 keeps Odoo out of the request path).
- Background jobs get their own correlation id per task execution (`task_<celery_task_id>`)
  — not inherited from an HTTP request, since sync/reconciliation runs are
  scheduler-triggered, not request-triggered. Where a task is triggered *by* a request
  (e.g., order export enqueued right after order creation), the originating request's
  correlation id is carried into the task payload so the two are traceable together.

## 2. Structured logging

- JSON structured logs (not free-text) from both the FastAPI process and Celery
  workers — one log line per significant event, with consistent keys: `timestamp`,
  `level`, `correlation_id`, `module`, `event`, plus event-specific fields.
- No secrets or full card/payment data in logs, ever (rule 22's spirit extended to
  runtime data, not just source).
- Log levels used meaningfully: `INFO` for normal request/task completion and sync
  outcomes, `WARNING` for retried-but-recovered failures, `ERROR` for failures that need
  human attention (dead-lettered outbox events, reconciliation drift, Odoo auth failure).

## 3. Audit trail

Two kinds of audit record, both persisted in PostgreSQL (not log-only, since audit data
needs to survive log rotation/retention policy and be queryable from the admin UI later):

- **Admin mutation audit** — every admin-initiated write (product merchandising edit,
  staff role change, promo code change, order status override, etc.) writes an audit row:
  `actor_admin_id`, `action`, `entity_type`, `entity_id`, `before`, `after`, `at`,
  `correlation_id`. This is new relative to today's system, which has **no audit trail at
  all** for admin actions (explicitly noted as a gap in
  [gap-analysis.md](../current-state/gap-analysis.md) §6 — "no order-status transition
  validation... with no audit trail of who made the change").
- **Sync audit log** (`sync_audit_log`, §[integration-principles.md](integration-principles.md))
  — every worker run (product sync, order export, status import, reconciliation): started
  at, finished at, records processed/succeeded/failed, outcome, error summary. This is
  what makes rule 17's "auditable" concrete for the Odoo integration specifically, distinct
  from general admin-action auditing above.

## 4. Metrics

Minimum viable metric set (via a lightweight approach — e.g. `prometheus-client` exposing
`/metrics`, or push to whatever the deployment target already provides; no new heavyweight
observability stack introduced speculatively, consistent with the "no unjustified
infrastructure" stance in [target-architecture.md](target-architecture.md) §4):

- HTTP: request count/latency/status by route (standard FastAPI middleware instrumentation).
- Outbox: `pending`/`failed`/`dead` event counts by type — the primary signal for order-
  export health (§[integration-principles.md](integration-principles.md) §3).
- Sync tasks: last-successful-run timestamp and duration per task type — lets an operator
  see at a glance "product price sync hasn't succeeded in 2 hours" without reading logs.
- Reconciliation: drift count per run (order and product) — a non-zero, growing trend is
  the signal something upstream is quietly broken.

## 5. Alerting (target, not phase-one)

Not built in the first implementation slices, but the above is designed so it can be
wired to alerts later without rework: outbox `dead` count > 0, sync task overdue by more
than N× its schedule interval, reconciliation drift above a threshold. Called out
explicitly so "observable" (rule 17) isn't satisfied by logs nobody looks at.

## 6. Frontend error reporting

The existing Lovable-specific error-reporting hook
(`src/lib/lovable-error-reporting.ts`) only functions inside the Lovable editor preview
iframe and is dead weight in a real deployment
([frontend-architecture.md](../current-state/frontend-architecture.md)). Once the app is
deployed outside Lovable's own hosting, frontend runtime errors should be forwarded to
whatever the chosen deployment/observability target supports (e.g., a simple error-report
POST to a FastAPI endpoint that logs with the same correlation-id scheme, or a standard
error-tracking service) — decision deferred to
[implementation-roadmap.md](implementation-roadmap.md)'s hardening phase, not needed for
the architecture definition itself.
