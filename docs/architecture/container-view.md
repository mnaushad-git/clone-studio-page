# Container View

_C4 model, level 2 (Containers). Each box is an independently deployable/runnable unit.
See [deployment-topology.md](deployment-topology.md) for how these map to actual
environments._

## Containers

| Container | Technology | Responsibility | Talks to |
|---|---|---|---|
| **Customer Storefront / Admin Portal** | Existing TanStack Start app (React 19, TS), unchanged | Renders both UIs; SSR + browser. All data access goes through the FastAPI HTTP API. | FastAPI (HTTPS/JSON) only |
| **FastAPI API** | FastAPI, Python, modular monolith, SQLAlchemy 2.x, Pydantic | Thin request handlers → services → repositories. Serves catalogue, cart, checkout, orders, content, admin CRUD. Writes the transactional outbox row on order creation. Never calls Odoo synchronously in a request handler. | PostgreSQL (reads/writes), Redis (cache, rate limit, Celery enqueue) |
| **PostgreSQL** | PostgreSQL, managed in production | Sole operational datastore for the storefront/admin runtime: catalogue cache, merchandising content, carts, checkout state, orders (pre- and post-sync), outbox, sync checkpoints, audit/reconciliation records. | Read/written only by FastAPI and by workers |
| **Redis** | Redis | Celery broker + result backend; response/query caching; rate limiting. | FastAPI, workers |
| **Background Workers** | Celery workers, Python, same codebase as FastAPI (`backend/app/workers/`) | Execute product/price/availability sync from Odoo, order export to Odoo, order-status import, retries, reconciliation. All Odoo access goes through the integration adapter. | PostgreSQL, Redis, Odoo integration adapter |
| **Scheduler (Celery Beat)** | Celery Beat | Fires scheduled sync/reconciliation tasks per [component-view.md](component-view.md) §Worker & Scheduler Responsibilities. Single active instance to avoid duplicate schedules. | Redis (enqueues into the same broker workers consume) |
| **Odoo Integration Adapter** | Python module inside the backend codebase (`backend/app/integrations/odoo/`), not a separate deployable | Isolates all Odoo-specific request/response shapes, auth, and API calls (XML-RPC/JSON-RPC/REST — TBD, see [integration-principles.md](integration-principles.md)) behind an internal interface the rest of the backend uses. | Odoo, over the network, using supported APIs only |
| **Odoo** | External system, not part of this deployment | ERP system of record — see [system-context.md](system-context.md). | Reached only by the integration adapter, from workers (and, for the authenticated status-callback path, from a narrowly scoped FastAPI webhook endpoint — see [integration-principles.md](integration-principles.md)) |

## Container diagram

```
┌───────────────────────────────┐
│ Customer Storefront /          │
│ Admin Portal (existing UI)      │
└───────────────┬─────────────────┘
                 │ HTTPS /api/v1/*
                 ▼
┌───────────────────────────────────────────┐        ┌───────────────┐
│ FastAPI API (modular monolith)              │◄──────►│ Redis          │
│  routes → services → repositories            │        │ (broker/cache) │
└───────┬─────────────────────────┬─────────────┘        └───────┬───────┘
        │ SQL                     │ enqueue                       │ consume
        ▼                         ▼                                ▼
┌───────────────────┐   ┌─────────────────────────────────────────────┐
│ PostgreSQL          │◄──┤ Background Workers (Celery) + Beat scheduler │
│ operational DB       │  │  product/price/availability sync,            │
└───────────────────┘   │  order export, status import, retry,          │
                          │  reconciliation                               │
                          └───────────────────┬─────────────────────────┘
                                               │ supported Odoo APIs only
                                               ▼
                                  ┌───────────────────────────┐
                                  │ Odoo Integration Adapter    │
                                  │ (in-process module)         │
                                  └───────────────┬─────────────┘
                                                  ▼
                                       ┌───────────────────┐
                                       │ Odoo (ERP, external)│
                                       └───────────────────┘
```

## Why the adapter is not its own service

The Odoo integration adapter is a Python module inside the same codebase/process family
as the FastAPI app and the Celery workers — not a separate microservice. It is *logically*
isolated (own package, own tests, own interface) but *physically* deployed as part of the
backend image, imported by both the API (for the authenticated status-callback endpoint,
if used instead of polling) and the workers (for scheduled sync). This keeps the system a
modular monolith per [target-architecture.md](target-architecture.md) §4 while still
giving rule 16 ("Odoo-specific logic must remain inside an isolated integration adapter")
a real code boundary, enforceable by import-linting rather than a network hop.
