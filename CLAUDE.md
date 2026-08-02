# CLAUDE.md — Terrific Bites

Guidance for Claude Code (and any other agent) working in this repository.

## What this repo is today

A single **TanStack Start** (React 19 + TypeScript) application generated and actively
maintained through **Lovable** (lovable.dev). It contains two UIs in one codebase:

- **Customer Storefront** — public bakery e-commerce site (`src/routes/*`, excluding `admin.*`)
- **Admin Portal** — `/admin/*` routes, separate layout/shell, same codebase

There is currently **no backend**. All "data" is hardcoded TypeScript literals or two
`localStorage`-backed stores (`src/lib/store.ts`, `src/lib/admin-store.ts`). Supabase is
provisioned but unwired (zero tables, not imported by any route). Full detail:
[docs/current-state/](docs/current-state/) (repository audit, dated 2026-07-27).

## Where this is headed

A target architecture has been defined but **not yet implemented**. Full detail:
[docs/architecture/](docs/architecture/), start with
[target-architecture.md](docs/architecture/target-architecture.md).

Summary: Storefront/Admin UI → **FastAPI** → **PostgreSQL** (operational data) +
**background workers** (Celery) → **Odoo** (ERP system of record for products, pricing,
tax, inventory, sales orders, invoicing, accounting).

## Non-negotiable architecture rules

These apply to all future backend work in this repo. See
[target-architecture.md](docs/architecture/target-architecture.md) for full rationale.

1. Browser code calls **FastAPI only** — never Odoo, never PostgreSQL directly.
2. PostgreSQL is the storefront's operational runtime database; normal requests are served
   from it **without synchronous Odoo calls**.
3. Odoo remains the ERP and authoritative source for product identity/SKU/variants,
   commercial price, tax, ERP inventory, sales orders (post-sync), invoices, accounting,
   and ERP fulfilment status. **Never write directly to the Odoo database** — supported
   Odoo APIs only.
4. Products flow **Odoo → background worker → PostgreSQL**. Orders flow
   **PostgreSQL transactional outbox → background worker → Odoo**. Order status flows
   **Odoo → background worker or authenticated callback → PostgreSQL**.
5. Long-running or synchronous-to-Odoo work happens in **background workers**, never
   inside a FastAPI request handler.
6. FastAPI routes are thin; business logic lives in **service classes**; database access
   lives in **repository classes**; all Odoo-specific logic is isolated in an
   **integration adapter** (`app/integrations/odoo/`).
7. Product and order sync must be **idempotent, retryable, auditable, observable**.
8. Order creation and its outbox event commit in **one PostgreSQL transaction**.
9. Odoo-controlled commercial fields and Admin-Portal-controlled merchandising fields are
   kept in **separate tables/columns** — see
   [data-ownership.md](docs/architecture/data-ownership.md).

## What must be preserved

- The existing Storefront and Admin Portal UI, routes, layouts, and responsive behaviour —
  **do not redesign**. The UI is treated as the product specification.
- English/Arabic bilingual support and RTL layout.
- This branch syncs with the Lovable editor (see `AGENTS.md`) — avoid force-push,
  rebase, or amend of pushed history; keep the branch in a working state.

## Working conventions

- **Modular monolith**, not microservices. Do not introduce Kafka, Kubernetes, event
  sourcing, CQRS, Elasticsearch, or DB replication without a demonstrated need — see
  [architecture-decision-records.md](docs/architecture/architecture-decision-records.md).
- Backend stack: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic, PostgreSQL, Redis, Celery,
  pytest, Docker Compose for local dev.
- Secrets are never committed. Note: `.env` at repo root is currently tracked by git and
  contains only Supabase publishable-key material — do not add any secret (service-role
  key, DB password, Odoo credentials, JWT signing key) to a tracked file. Use
  `.env.local`/untracked env files and a secrets manager in deployed environments.
- No hardcoded production data (test fixtures and seed data must be clearly marked as such).
- Every implementation phase ships with tests and an actual command-verification step
  (see [testing-strategy.md](docs/architecture/testing-strategy.md)) — not just a claim
  that it works.

## Current status

Architecture definition only — **no backend functionality has been implemented yet**.
Do not start business-logic implementation until the architecture in
[docs/architecture/](docs/architecture/) has been reviewed and approved.
