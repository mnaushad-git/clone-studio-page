# Implementation Roadmap

Vertical-slice implementation sequence (task 17). Each slice is meant to be *thin but
real* end-to-end — not a layer (e.g., "build all repositories") across the whole system.
Per [testing-strategy.md](testing-strategy.md) and rule 24, every slice ships with tests
and an actual command-verification step; nothing here is implemented as part of this
architecture-definition pass (task 20 — do not implement yet).

## Sequence

1. **Backend foundation** — `backend/` scaffold: FastAPI app factory, `core/` (config,
   db session, error envelope, logging/correlation middleware), Alembic wired to an empty
   schema, Dockerfile, pyproject, CI running lint/type-check/pytest (even with near-zero
   tests at this point, the pipeline itself must exist and pass).
2. **PostgreSQL foundation** — initial Alembic migrations for the domain boundaries in
   [data-ownership.md](data-ownership.md) (empty/skeleton tables), docker-compose
   `postgres`/`redis` services, repository-layer base classes/session handling.
3. **Odoo client** — `integrations/odoo/client.py` + auth, against a real Odoo
   sandbox/staging instance; a minimal read call (e.g., list products) proven working with
   a contract test, before any business module depends on it.
4. **Current mock catalogue audit and normalisation** — take `src/lib/products.ts`'s 28
   products and the admin `categories`/`productOverrides` data and produce a clean,
   deduplicated dataset (resolving the three-sources-of-truth category problem,
   [target-architecture.md](target-architecture.md) C8) ready to become real Odoo records.
   Output is data + a mapping document, not application code.
5. **Catalogue import into Odoo** — load the normalised catalogue into the Odoo
   sandbox/staging instance via the supported API (not a manual UI import, so the same
   path is provable/repeatable for production cutover later).
6. **Odoo-to-PostgreSQL product sync** — the `catalogue` module + `product_sync` worker
   task (§[integration-principles.md](integration-principles.md) §2), running against the
   data imported in step 5, with idempotency/audit/observability in place from the start,
   not bolted on later.
7. **Catalogue APIs** — `/api/v1/products`, `/api/v1/products/{id}`, filtering/pagination
   (§[api-standards.md](api-standards.md)), backed by the synced PostgreSQL cache — the
   first endpoint a browser can actually call.
8. **Connect one existing frontend product section** — one real storefront surface (e.g.
   `/shop` via `ShopGrid`) switched from static `products.ts` to the new catalogue API,
   proving the full path browser → FastAPI → PostgreSQL (synced from Odoo) end-to-end,
   with the UI visually unchanged (rule 20).
9. **Homepage configuration** — `merchandising`/`content` modules + APIs, wiring
   `/admin/content` (banners, homepage sections) to actually affect `index.tsx` — closing
   the audit's §2.1 finding that this admin page currently has zero effect.
10. **Admin authentication** — real `admin_identity` module, RBAC, replacing the hardcoded
    password and closing the audit's §1.2–1.5 findings
    ([security-boundaries.md](security-boundaries.md) §3). Blocks any admin-portal API
    work beyond read-only content, since every admin mutation from here on assumes a real
    session.
11. **Admin Portal integration** — remaining admin CRUD screens (products/merchandising,
    categories, delivery zones/slots, promotions, staff, reviews, settings) wired to real
    APIs, one page at a time, each closing its corresponding audit gap
    ([gap-analysis.md](../current-state/gap-analysis.md) §2).
12. **Customer authentication** — real `customers` module
    ([security-boundaries.md](security-boundaries.md) §2), replacing the any-credentials
    login/signup flow.
13. **Cart** — `cart` module + API, replacing `store.ts`'s local cart with a
    server-persisted one (still fast/responsive client-side, backed by real writes).
14. **Checkout and payments** — `checkout` module, delivery slot/zone selection wired to
    real data (step 11), and a real tokenized-payment integration replacing the raw-card
    `payment.tsx` form's backend (UI shape preserved per rule 20; wire format changes
    underneath, per [security-boundaries.md](security-boundaries.md) §4).
15. **Local order creation** — `orders` module: order + order_item persisted in
    PostgreSQL, status `pending_sync` — this is the point at which a real order survives a
    cleared browser cache for the first time.
16. **Transactional outbox** — outbox table + the one-transaction guarantee (rule 18),
    wired into order creation (§[integration-principles.md](integration-principles.md) §3).
17. **Odoo order export** — `order_export` worker task consuming the outbox, creating real
    Odoo sales orders, idempotent on the internal order id.
18. **Odoo order-status import** — polling worker (+ optional authenticated callback,
    §[integration-principles.md](integration-principles.md) §4) reflecting Odoo fulfilment/
    invoice status back into PostgreSQL, feeding the existing `OrderStatusTimeline`/
    `/track/$id` UI with real data instead of the current `setTimeout` auto-advance.
19. **Integration monitoring** — metrics/dashboards for outbox depth, sync task health
    (§[observability.md](observability.md)) — turning the auditability built in from step 6
    onward into something an operator actually watches.
20. **Reconciliation** — order (hourly) and product (weekly) reconciliation jobs
    (§[integration-principles.md](integration-principles.md) §5).
21. **Performance and security hardening** — load/pagination tuning, rate limiting review,
    dependency/security audit, closing remaining lower-severity gaps from
    [gap-analysis.md](../current-state/gap-analysis.md) §4–§6 (RTL mega-menu direction,
    currency literal, locale-aware date formatting, etc.) opportunistically.
22. **Production deployment** — cutover per
    [deployment-topology.md](deployment-topology.md) §3, pointed at production Odoo.

## Recommended first implementation slice

**Step 1 (Backend foundation) through step 3 (Odoo client)**, ending at a proven,
tested, CI-gated "hello world" round trip: FastAPI app running locally via Compose, an
Alembic-managed empty PostgreSQL schema, and one real read call succeeding against an Odoo
sandbox — before any business logic. This is deliberately small: it validates the riskiest
unknowns (does the team have Odoo sandbox access, does the chosen Odoo API actually behave
as assumed, does the CI/test scaffolding work) before catalogue data or business logic
depend on any of it. See open questions below — several block even this first slice.

## Open assumptions and unresolved questions

Carried forward from the existing audit ([roadmap.md](../current-state/roadmap.md) §5)
where still relevant, plus new ones raised by this architecture pass:

1. **Odoo version/edition/hosting** — not yet confirmed. Determines which API
   (XML-RPC/JSON-RPC vs. a REST module) is available, and the production network path
   (§[integration-principles.md](integration-principles.md) §1,
   [deployment-topology.md](deployment-topology.md) §3). **Blocks step 3.**
2. **Odoo sandbox/staging access for development** — needed before step 3 can start in
   practice, not just in principle.
3. **Supabase disposition** — retire entirely, or repurpose the already-provisioned
   project as a plain Postgres host / object-storage provider (never as the browser-facing
   Auth/BaaS layer, which would violate rule 1)? See
   [ADR-005](architecture-decision-records.md#adr-005). Affects step 2 (which Postgres
   instance is "the" operational database) and the object-storage question in
   [system-context.md](system-context.md).
4. **Payment provider** for the GCC market (Moyasar, HyperPay, Tap, PayTabs, or a global
   provider with regional support) — the existing UI already lists Mada/STC Pay/Apple Pay
   as method options; affects step 14's integration shape.
5. **Notification provider(s)** for OTP/email/SMS — is SMS required in addition to email
   (common GCC expectation)? Affects step 12 (customer auth) and order-status
   notifications.
6. **Tenancy model** — single-brand only, or is multi-tenant/white-label ever in scope?
   Affects whether any table needs a `tenant_id` from day one (cheap to add now, expensive
   to retrofit) — carried forward from [roadmap.md](../current-state/roadmap.md) §5.1.
7. **Staff RBAC matrix specifics** — the five roles exist in the UI today
   (`owner/admin/manager/support/kitchen`) but the exact per-role permission boundary
   (who can edit settings, staff, orders, content) needs to be specified before step 10's
   RBAC implementation, not just "roles exist."
8. **Multi-city/multi-currency** — is expansion beyond Riyadh an active near-term goal, or
   should `location.ts`'s 8-city model be simplified for now? Affects catalogue/pricing
   design (per-city pricing?) and the currency-literal cleanup in step 21.
9. **Lovable workflow going forward** — does active development continue through the
   Lovable editor in parallel with backend engineering? This affects how safely the
   `backend/` addition and any frontend API-client wiring can proceed without conflicting
   with Lovable-side prompt-driven changes, and confirms the repo-structure recommendation
   in [target-architecture.md](target-architecture.md) §7 (frontend must stay at repo
   root, unmoved, for Lovable's sync to keep working).
10. **Seed/demo data disposition** — should the current seeded reviews, staff, promo
    codes, and 28-product catalogue become real starting data (step 4's normalisation
    target), or are they placeholder content to be fully replaced before launch?
11. **Which gap-analysis findings are "fix as part of this migration" vs. "backlog"** —
    e.g. the discarded gift-message feature, dead footer links — confirm scope before step
    21 so hardening doesn't silently expand into a redesign (rule 20 boundary).
12. **CI/hosting provider choice** for production (§[deployment-topology.md](deployment-topology.md))
    — not yet selected; affects step 22 concretely but doesn't block earlier steps.
