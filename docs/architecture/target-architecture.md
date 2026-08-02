# Target Architecture — Terrific Bites

_Status: proposed, unimplemented. No backend code exists yet — this document defines what
to build, not a record of what has been built. Based on the repository audit in
[docs/current-state/](../current-state/) (audit date 2026-07-27) and the actual repo tree
as of this document's date._

## 1. Why this document exists

The current repository ([project-overview.md](../current-state/project-overview.md)) is a
fully client-side prototype: two `localStorage` blobs stand in for a database, customer
and admin "auth" accept arbitrary credentials, and Supabase is provisioned but unused.
The UI itself — ~40 storefront and admin routes, a consistent design system, working
bilingual/RTL support — is judged complete enough to serve as the product specification
([roadmap.md](../current-state/roadmap.md) §1). This document defines the target backend
architecture that gives that UI a real, secure, persistent, ERP-integrated system, without
redesigning it.

## 2. High-level architecture

```
                    ┌─────────────────────────────────────────┐
                    │   Customer Storefront / Admin Portal     │
                    │   (existing TanStack Start app, at       │
                    │    repo root — UI unchanged)              │
                    └───────────────────┬───────────────────────┘
                                         │ HTTPS, JSON, /api/v1/*
                                         │ (browser calls FastAPI ONLY)
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │              FastAPI (modular monolith)  │
                    │  thin routes → services → repositories   │
                    └───────┬───────────────────────┬───────────┘
                            │                        │
                            ▼                        ▼
                 ┌─────────────────────┐   ┌───────────────────────┐
                 │ PostgreSQL           │   │ Redis                  │
                 │ operational database │   │ (Celery broker/result, │
                 │ (storefront runtime) │   │  cache, rate limiting) │
                 └─────────┬─────────────┘   └───────────┬─────────────┘
                            │  reads/writes                │ enqueue/schedule
                            │  (outbox table lives here)   ▼
                            │                  ┌───────────────────────────┐
                            │◄─────────────────┤ Background Workers         │
                            │  writes results  │ (Celery workers + beat)    │
                            │                  └───────────┬─────────────────┘
                            │                              │ supported Odoo APIs only
                            │                              ▼
                            │                  ┌───────────────────────────┐
                            │                  │ Odoo integration adapter   │
                            │                  │ (isolated, versioned)      │
                            │                  └───────────┬─────────────────┘
                            │                              │ XML-RPC/JSON-RPC/REST
                            │                              ▼
                            │                  ┌───────────────────────────┐
                            └─────────────────►│ Odoo (ERP system of record)│
                               (no direct link) │ products, price, tax,      │
                                                 │ inventory, sales orders,   │
                                                 │ invoices, accounting       │
                                                 └───────────────────────────┘
```

The browser has exactly one backend dependency: FastAPI. PostgreSQL and Odoo are never
reachable from the browser, directly or via a leaked client SDK.

## 3. Core architecture rules

Restated from the brief, treated as constraints on every future implementation phase:

1. Storefront and Admin Portal call FastAPI only.
2. Browser code never calls Odoo directly.
3. Browser code never connects directly to PostgreSQL.
4. PostgreSQL is the operational runtime database for the storefront.
5. Odoo remains ERP and authoritative source for: product identity, SKU, variants,
   commercial price, tax configuration, inventory/ERP availability, sales orders
   (post-sync), invoices, accounting, ERP fulfilment status.
6. Normal storefront requests are served from PostgreSQL without synchronous Odoo calls.
7. Products flow **Odoo → background worker → PostgreSQL**.
8. Orders flow **PostgreSQL transactional outbox → background worker → Odoo**.
9. Order status flows **Odoo → background worker or authenticated callback → PostgreSQL**.
10. Odoo integration uses supported APIs only.
11. No direct writes to the Odoo database.
12. Long-running synchronisation runs in background workers, not FastAPI request handlers.
13. FastAPI route handlers stay thin.
14. Business logic stays in service classes.
15. Database access stays in repository classes.
16. Odoo-specific logic stays inside an isolated integration adapter.
17. Product/order sync is idempotent, retryable, auditable, observable.
18. Order creation and its outbox event commit in one PostgreSQL transaction.
19. Odoo-controlled commercial fields are separated from Admin-Portal-controlled
    merchandising fields.
20. Existing working UI, routes, layouts, responsive behaviour are not redesigned.
21. English, Arabic, and RTL support are preserved.
22. Secrets are never committed.
23. Production data is never hardcoded.
24. Every implementation phase includes tests and actual command verification.

## 4. Architecture style

**Modular monolith.** One FastAPI process (scaled horizontally by running more replicas),
organized into clearly bounded modules (§6 in [component-view.md](component-view.md)),
each with its own service + repository + schema layer. One PostgreSQL database, organized
by logical domain (schemas or well-namespaced tables — see
[data-ownership.md](data-ownership.md)). One Redis instance for Celery + cache. One
Odoo instance, reached exclusively through the integration adapter.

**Explicitly not used**, per the brief, unless a demonstrated requirement justifies them
later (see [ADR-001](architecture-decision-records.md#adr-001)):
microservices, Kafka, Kubernetes, event sourcing, CQRS, Elasticsearch, direct database
replication. At current scale (single-brand GCC bakery e-commerce, tens of products,
low-thousands of orders/day at most), none of these are justified — they would add
operational surface area without solving a problem this system actually has.

## 5. Existing code vs. target architecture — conflicts found

| # | Existing state | Conflicts with | Recommendation |
|---|---|---|---|
| C1 | `src/integrations/supabase/client.ts` is a **browser-side** Supabase client (publishable key). Currently unused by any route, but it is live-wired scaffolding (`start.ts` registers `attachSupabaseAuth` globally). | Rule 1/2 (browser calls FastAPI only) — any future use of this client for Auth, Storage, or direct table reads would let the browser talk to a backend other than FastAPI. | Do not build on this client. Either retire it, or keep it strictly out of the request path (see [ADR-005](architecture-decision-records.md#adr-005)). |
| C2 | `src/integrations/supabase/client.server.ts` is a **service-role** Postgres-adjacent client intended to be called from TanStack Start server functions, bypassing RLS. | Rule 3 conceptually (server-side direct DB access from the *frontend's own server runtime*, not FastAPI) and rule 15 (DB access must live in repository classes inside the backend, not the frontend server). | Do not extend this pattern. All persistent data access happens through FastAPI; the frontend's SSR layer should call FastAPI over HTTP like the browser does, not open its own DB connection. |
| C3 | Old roadmap ([roadmap.md](../current-state/roadmap.md) §4.2) recommended growing directly into **Supabase Auth** for customers. | Rule 1 — that pattern issues the browser a Supabase session directly, bypassing FastAPI as the sole backend boundary. | Superseded. Customer and admin auth are issued and verified by FastAPI (§13). Supabase Auth is not used. See open question in §11. |
| C4 | `src/lib/store.ts` and `src/lib/admin-store.ts` hold **all** state (including config that will become Odoo-owned, e.g., nothing product-authoritative today, but `productOverrides` already anticipates a split) in one client-writable `localStorage` blob with no server round-trip. | Rules 2, 3, 6, 19 — no server boundary exists today, and there is no separation yet between commercial (future Odoo-owned) and merchandising (future Postgres-owned) product fields. | Confirms the roadmap's own framing: replace store internals with FastAPI calls per domain, one vertical slice at a time (§17 / [implementation-roadmap.md](implementation-roadmap.md)). Do not attempt a big-bang rewrite. |
| C5 | Admin auth is a hardcoded password (`"admin123"`) checked client-side, with no RBAC ([gap-analysis.md](../current-state/gap-analysis.md) §1.2–1.5). | Rule 13/14 (no service layer exists to enforce this server-side at all) and the general expectation of real authentication. | Must be replaced, not patched, as part of the Admin Authentication slice (§17 step 10). This is the highest-severity pre-existing gap. |
| C6 | `admin.tsx`'s route guard reads `localStorage` directly in `beforeLoad`, and the check is a no-op during SSR (`if (typeof window === "undefined") return`). | Same as C5 — no real session validation exists to guard against. | Replace with a real session check against a FastAPI-issued token, validated both server-side (SSR loader) and client-side. |
| C7 | Product catalog is a static 28-item TypeScript array (`src/lib/products.ts`); there is no product creation flow anywhere in the admin UI. | Rule 5/7 — products must originate in Odoo and flow to PostgreSQL via a worker; the array can't be the source of truth going forward. | Requires the **catalogue import into Odoo** step (§17 step 5) — the current mock catalogue must first be audited and normalised into a real Odoo product set before any sync worker has something correct to read. |
| C8 | Two disconnected category sources of truth (`admin-store.ts`'s `categories`, `products.ts`'s `Category` union, `ShopGrid`'s own hardcoded `CATEGORIES`) — [components.md](../current-state/components.md) §"Cross-cutting". | Not a hard rule violation, but directly undermines rule 19 (clean commercial/merchandising split) if carried forward as-is. | Must be unified as part of the catalogue-sync design (§17 steps 4–7): category becomes a synced Odoo/PostgreSQL field, not three parallel lists. |
| C9 | `.env` at repo root is tracked by git (contains only a Supabase publishable key today — acceptable by Supabase's own design, but the file is not gitignored). | Rule 22 (secrets never committed) — no violation yet, but the guardrail isn't in place. | Add backend secret files (`.env`, `.env.local`, any Odoo/DB credentials file) to `.gitignore` **before** any real secret is generated. Treat the current tracked `.env` as a housekeeping fix, not a live leak. |
| C10 | No test framework, no CI, anywhere in the repo ([gap-analysis.md](../current-state/gap-analysis.md) §5). | Rule 24 (every phase ships tests + verification). | Backend work introduces pytest + CI from the first slice, not retrofitted later (see [testing-strategy.md](testing-strategy.md)). |

No conflict above requires touching the existing storefront/admin UI code to resolve —
they are all resolved by what gets built *behind* it.

## 6. Storefront/Admin Portal: one frontend project or two?

**Recommendation: remain one frontend project.** Do not split into two applications.

Reasoning, grounded in the actual implementation:

- They already share the entire design system (`src/components/ui/*`, Tailwind theme
  tokens in `src/styles.css`), the i18n engine and dictionaries (`src/lib/i18n*`), build
  tooling, and TypeScript config. Splitting would mean either duplicating all of that or
  extracting a shared package — real cost with no corresponding benefit at this scale.
- The admin portal is already route-namespaced (`/admin/*`) with its own layout
  (`admin.tsx`) and does not share chrome (`SiteHeader`/`SiteFooter`/`MegaMenu`/
  `CartDrawer`) with the storefront — the *code-level* separation the split would buy
  already exists at the routing layer.
- The repo is Lovable-managed (`AGENTS.md`): Lovable pushes directly to this branch at the
  repo root. Splitting into two applications/repos would require reconfiguring or
  abandoning that sync relationship — a decision with real workflow cost that belongs to
  the user, not something to default into silently (see open question in §11).
- The actual problem the current architecture has is not "one codebase" — it's "no
  server-side trust boundary." Two frontend apps calling the same unauthenticated
  `localStorage` would have the identical security gap. A real FastAPI backend with
  separate customer/admin auth (§13) gives the two portals a genuine boundary without a
  repo split.
- Splitting can be revisited later if the admin portal needs an independent deploy
  cadence, a separate network/VPN perimeter, or a different team owns it — none of which
  is true today.

## 7. Proposed repository structure

The existing frontend stays exactly where it is, untouched, at the repo root (Lovable
continues to own `src/`, `public/`, etc.). New backend code is added alongside it:

```
Terrific_Bites/
├── src/                        # EXISTING — Lovable-owned frontend, unchanged
├── public/                     # EXISTING — unchanged
├── supabase/                   # EXISTING stub — disposition: see ADR-005 (likely retired
│                                #   or repurposed as a plain Postgres host, not BaaS)
├── docs/
│   ├── current-state/          # EXISTING — repository audit, kept as historical record
│   └── architecture/           # THIS set of documents
├── backend/                    # NEW — FastAPI modular monolith
│   ├── app/
│   │   ├── main.py             # app factory, router mounting, middleware
│   │   ├── api/v1/             # thin route handlers only, one file per resource group
│   │   ├── modules/            # business modules: schemas + service + repository each
│   │   │   ├── catalogue/
│   │   │   ├── merchandising/
│   │   │   ├── cart/
│   │   │   ├── checkout/
│   │   │   ├── orders/
│   │   │   ├── outbox/
│   │   │   ├── customers/
│   │   │   ├── admin_identity/
│   │   │   ├── promotions/
│   │   │   ├── delivery/
│   │   │   ├── reviews/
│   │   │   ├── loyalty/
│   │   │   └── content/
│   │   ├── integrations/
│   │   │   └── odoo/           # isolated Odoo adapter — see integration-principles.md
│   │   ├── workers/            # Celery app, beat schedule, tasks — see component-view.md
│   │   ├── core/                # config, db session, security, logging, error envelope
│   │   └── db/alembic/         # migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── Dockerfile
│   └── .env.example            # NEVER a real .env
├── docker-compose.yml           # NEW — local dev: postgres, redis, backend api,
│                                #   celery worker, celery beat
├── CLAUDE.md                    # project guidance (this repo)
├── AGENTS.md                    # EXISTING — Lovable sync warning, unchanged
└── README.md                    # EXISTING, to be updated once backend lands
```

Rationale: a single monorepo keeps frontend/backend changes reviewable together during
the migration (many slices touch both), while `backend/` as its own top-level directory
with its own `pyproject.toml`/`Dockerfile` keeps it independently buildable, testable, and
deployable. This avoids introducing a second repository (and the coordination overhead of
cross-repo versioning) without justification, consistent with §4's bias against
unnecessary structure.

## 8. Related documents

- [system-context.md](system-context.md) — actors and external systems
- [container-view.md](container-view.md) — deployable units and their communication
- [component-view.md](component-view.md) — backend module boundaries, frontend service
  boundaries, worker/scheduler responsibilities
- [data-ownership.md](data-ownership.md) — field-by-field Odoo vs. PostgreSQL ownership
- [integration-principles.md](integration-principles.md) — Odoo integration boundaries,
  sync patterns, idempotency/retry/audit design
- [api-standards.md](api-standards.md) — versioning, error envelope, conventions
- [security-boundaries.md](security-boundaries.md) — customer vs. admin auth
- [observability.md](observability.md) — logging, audit, correlation IDs
- [testing-strategy.md](testing-strategy.md)
- [deployment-topology.md](deployment-topology.md)
- [implementation-roadmap.md](implementation-roadmap.md) — vertical-slice sequence
- [architecture-decision-records.md](architecture-decision-records.md)
