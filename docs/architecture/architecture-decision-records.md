# Architecture Decision Records

Task 18: architecture decisions worth recording formally. Written in lightweight ADR form
(context / decision / consequences) inline here rather than as separate numbered files,
since the set is small enough to stay legible as one document — split into individual
`docs/architecture/adr/NNNN-*.md` files later if the team's process wants that.

## ADR-001: Modular monolith, not microservices

**Context**: The brief explicitly asks that microservices, Kafka, Kubernetes, event
sourcing, CQRS, Elasticsearch, and DB replication not be introduced without a demonstrated
requirement. Current/expected scale: single-brand GCC bakery e-commerce, a few dozen
products, guest+registered customers, admin staff in the single digits/low tens.

**Decision**: One FastAPI process (horizontally replicated), one PostgreSQL database, one
Redis instance, Celery for workers/scheduling. Module boundaries are enforced in code
(service/repository layering, import discipline), not by network/process separation.

**Consequences**: Lower operational overhead, simpler local dev (`docker-compose up`),
easier transactional guarantees (the outbox pattern, rule 18, is trivial in one DB and
would require a saga/distributed-transaction pattern across services). Revisit only if a
specific module demonstrably needs independent scaling/deployment that the monolith can't
provide — not preemptively.

## ADR-002: PostgreSQL as operational store; Odoo remains ERP of record

**Context**: Rules 4–6, 10–11. The system needs fast, always-available storefront reads
that cannot depend on Odoo's availability or latency.

**Decision**: PostgreSQL is written to directly by FastAPI/workers for all storefront
runtime data; Odoo is never queried synchronously inside a request handler and is never
written to directly (no raw SQL against Odoo's database) — only through supported APIs,
only from background workers/the integration adapter.

**Consequences**: Storefront stays fast and available independent of Odoo's uptime; the
cost is eventual consistency (product/price/availability lag by the sync interval,
order/status lag similarly) — acceptable per the scheduling assumptions in
[component-view.md](component-view.md) §4, and made visible via reconciliation
(§[integration-principles.md](integration-principles.md) §5) rather than hidden.

## ADR-003: Transactional outbox for order export

**Context**: Rule 18 requires order creation and its export event to commit atomically;
Odoo may be temporarily unreachable at the moment of order placement.

**Decision**: Use the transactional-outbox pattern (§[integration-principles.md](integration-principles.md)
§3) rather than a synchronous call to Odoo during checkout, and rather than a message
broker/event-sourcing setup (explicitly out of scope per the brief).

**Consequences**: Orders are never lost even if Odoo or the worker is down at checkout
time; the tradeoff is that "sent to Odoo" is asynchronous, so the UI must reflect
`pending_sync` honestly rather than implying instant ERP confirmation (already how
`success.tsx`'s status timeline concept works today, just against a real state machine
instead of a `setTimeout`).

## ADR-004: Celery + Redis for workers and scheduling

**Context**: Need background workers (product/order sync, retries, reconciliation) and a
scheduler (Celery Beat-style periodic tasks), per the preferred technology baseline.

**Decision**: Celery with Redis as broker + result backend, run as separate
worker/beat processes sharing the backend codebase (§[container-view.md](container-view.md)).

**Consequences**: Mature, well-understood Python ecosystem fit for FastAPI; Redis is
already needed for caching/rate-limiting, so no extra infrastructure component is
introduced solely for this. Beat must run as a single instance (§[deployment-topology.md](deployment-topology.md)
§3) — an operational constraint to respect, not a design flaw.

## ADR-005: Disposition of the existing Supabase scaffolding

**Context**: `src/integrations/supabase/*` is fully wired (client, server client, auth
middleware, generated types) but has zero tables and is called from nowhere in the app
today ([frontend-architecture.md](../current-state/frontend-architecture.md)). The old
roadmap recommended growing into Supabase Auth; the new mandate (rule 1) requires the
browser to call FastAPI only.

**Decision (proposed, pending user confirmation — see [implementation-roadmap.md](implementation-roadmap.md)
open question 3)**: Do not build customer/admin auth on Supabase Auth from the browser.
Either (a) retire the Supabase project and its scaffolding entirely once a real PostgreSQL
instance is provisioned, or (b) repurpose the already-provisioned Supabase project as a
plain managed-Postgres host (and optionally object storage for images/review photos),
reached only from the backend with a standard connection string — never via the browser
SDK, never via its Auth/RLS layer. Default recommendation is (b) for cost/speed (infra
already exists), but this is explicitly a decision for the user, not decided unilaterally
here.

**Consequences**: `src/integrations/supabase/client.ts` (browser client) and
`auth-attacher.ts`/`auth-middleware.ts` (Supabase-Auth-shaped middleware) become dead code
to be removed once the real auth (step 10/12 of the roadmap) lands — they are not the
foundation the new auth is built on, regardless of which option is chosen.

## ADR-006: Storefront and Admin Portal remain one frontend project

**Context**: Task 4 — evaluated in full in [target-architecture.md](target-architecture.md)
§6.

**Decision**: No repository/application split. Both stay in the existing TanStack Start
app, unchanged in structure.

**Consequences**: Shared design system/i18n/build tooling stays shared (no duplication);
the security boundary the split might have implied instead comes from real server-side
auth (§[security-boundaries.md](security-boundaries.md)), which is required regardless of
repo topology. Revisit if the admin portal later needs an independent deploy cadence or
network perimeter a monorepo can't express.

## ADR-007: Repo topology — monorepo, backend added alongside existing frontend

**Context**: Task 5. The frontend is Lovable-managed and pushes directly to this repo's
root (`AGENTS.md`).

**Decision**: Add `backend/` as a new top-level directory in the same repository; do not
move or restructure the existing `src/`/`public/` frontend files.

**Consequences**: Keeps the Lovable sync relationship intact (a real constraint, not a
preference) and keeps frontend/backend changes reviewable together during the migration.
`backend/` has its own `pyproject.toml`/`Dockerfile`/CI job so it remains independently
buildable/deployable despite living in the same repo.

## ADR-008: Odoo integration protocol — deferred, default assumption stated

**Context**: Odoo version/edition/hosting is not yet confirmed (open question).

**Decision**: Design the adapter interface (`product_adapter`, `order_adapter`) against
internal DTOs now, independent of transport; default to targeting Odoo's standard
XML-RPC/JSON-RPC external API (available on every edition, no extra module required)
unless the confirmed Odoo instance makes a REST-based module a better fit.

**Consequences**: The rest of the backend is insulated from this choice
(§[integration-principles.md](integration-principles.md) §1) — confirming the actual
protocol later only touches `client.py`/`mappers.py`.

## ADR-009: Token-based sessions for customer and admin auth, separate audiences

**Context**: Task 13. Need a session mechanism that works with TanStack Start's SSR model
and gives a hard boundary between customer and admin capability.

**Decision**: FastAPI-issued tokens (JWT or opaque — final format is an implementation
detail, not architecturally load-bearing) with distinct `customer`/`admin` audiences/claims,
delivered as httpOnly cookies for the web client
(§[security-boundaries.md](security-boundaries.md)).

**Consequences**: A single compromised/misused token cannot cross the customer/admin
boundary; SSR route guards can validate the same cookie server-side (fixing today's
SSR-no-op guard bug) and client-side identically.

## ADR-010: Idempotency key = internal order UUID for order export

**Context**: Rule 17 requires order export to be idempotent; retries (§[integration-principles.md](integration-principles.md)
§3, §6) must not create duplicate Odoo sales orders.

**Decision**: The internal order UUID is passed to Odoo as a client order reference field
and checked before creating a new sales order on every export attempt.

**Consequences**: Safe to retry order export indefinitely without operator intervention
for the "was it actually sent?" question — the check is against Odoo's own state, not
just the outbox's local bookkeeping, so it's correct even if the outbox event's own status
update failed to persist after a successful Odoo call.
