# Component View

_C4 model, level 3 (Components), scoped to the FastAPI backend and its relationship to the
existing frontend. Covers tasks 6, 7, and 10 from the architecture brief: backend module
boundaries, frontend service boundaries, worker/scheduler responsibilities._

## 1. Backend layering (applies inside every module)

Every module in `backend/app/modules/<name>/` follows the same three layers, per rules
13–16 in [target-architecture.md](target-architecture.md):

```
api/v1/<resource>.py   → route handlers only: parse request, call one service method,
                          shape the response. No business logic, no direct DB/session use.
modules/<name>/service.py → business logic: validation, orchestration, transaction
                          boundaries, calling repositories and (only from allowed modules)
                          the outbox or the Odoo adapter.
modules/<name>/repository.py → all SQLAlchemy queries for this module's tables. No
                          business logic. Returns ORM objects or module-local DTOs.
modules/<name>/models.py   → SQLAlchemy 2.x ORM models for this module's tables.
modules/<name>/schemas.py  → Pydantic request/response models.
```

Cross-module calls go through a service's public methods, never through another module's
repository directly — this keeps table ownership (§ [data-ownership.md](data-ownership.md))
enforceable at the code level.

## 2. Backend module boundaries

| Module | Owns | Depends on |
|---|---|---|
| `catalogue` | Product/variant read cache synced from Odoo: id mapping, SKU, name, base price, tax class, ERP availability, active flag. Read-mostly from the API's perspective — writes only come from the product-sync worker. | `integrations.odoo` (via worker, not directly), `outbox`/audit for sync logging |
| `merchandising` | Admin-owned product presentation: display order, badges, marketing description overrides, homepage section membership, banners. Joins to `catalogue` by product id, never duplicates Odoo-owned fields. | `catalogue` (read) |
| `content` | Homepage sections, moments, recipients, static content pages. | `merchandising` (for product placement) |
| `cart` | Cart + cart line items, keyed by session/customer. | `catalogue` (price/availability lookups), `customers` |
| `checkout` | Checkout session state, delivery slot/zone selection, promo application, payment reference (opaque token from the payment provider, never raw card data). | `cart`, `delivery`, `promotions`, `customers` |
| `orders` | Order + order line items + status history, **and** the transactional outbox table (same module — see §3). Storefront order is authoritative in PostgreSQL until Odoo sync confirms; post-sync, Odoo is authoritative for fulfilment/invoice status, and this module stores the synced reflection. | `checkout` (order creation input), `outbox` |
| `outbox` | Generic transactional-outbox primitive (event table + dispatch bookkeeping) used by `orders` (and any future module needing the same guarantee). | none (leaf module) |
| `customers` | Customer identity, sessions, saved addresses. | none (leaf module) |
| `admin_identity` | Staff accounts, roles, admin sessions, RBAC checks. | none (leaf module) |
| `promotions` | Promo codes, usage tracking (fixing the audit's finding that usage limits aren't enforced — [gap-analysis.md](../current-state/gap-analysis.md) §2.5). | `orders` (usage increment on confirmed order) |
| `delivery` | Delivery zones, slots, fee calculation. | none |
| `reviews` | Product reviews, moderation state. | `catalogue`, `customers` |
| `loyalty` | Points ledger, redemption. | `customers`, `orders` |
| `integrations.odoo` | Isolated adapter: auth, request/response mapping, retry/backoff, all Odoo API calls. No business logic — pure translation + transport. | Odoo (external) only |
| `workers` | Celery tasks that orchestrate sync using the modules above + the Odoo adapter. Tasks contain orchestration, not business rules (those stay in the relevant module's service). | `catalogue`, `orders`, `outbox`, `integrations.odoo` |

## 3. The transactional outbox (rule 8, rule 18)

`orders.service.create_order()` does, in one PostgreSQL transaction:

1. Insert the `order` row and `order_item` rows (status: `pending_sync`).
2. Insert one `outbox_event` row (`event_type=order_created`, `payload`, `status=pending`,
   `order_id` FK).
3. Commit.

A worker polls (or is notified of) `outbox_event` rows with `status=pending`, calls the
Odoo adapter to create the corresponding sales order, and updates the event row's status
(`sent` / `failed`) plus the order's `odoo_sale_order_id`/`sync_status` — never the reverse
order. If step 3's commit fails, neither the order nor the event exists; if it succeeds,
the event is guaranteed to exist for the worker to eventually process, even if the worker
is down at the moment of order creation. This is what makes order export retryable without
losing orders, without needing a distributed transaction or an event broker.

## 4. Worker and scheduler responsibilities

Celery workers execute tasks; Celery Beat schedules them. All schedules below are initial
targets (configurable), per the brief:

| Task | Schedule | Direction | Idempotency key |
|---|---|---|---|
| Product descriptive sync | 07:00 and 14:00 Asia/Riyadh | Odoo → PostgreSQL | Odoo product id |
| Product price sync | every 15–30 min (configurable) | Odoo → PostgreSQL | Odoo product id |
| Product availability sync | every 5 min (configurable) | Odoo → PostgreSQL | Odoo product id |
| Order export | near real-time (triggered by outbox insert, plus a short-interval sweep as a safety net) | PostgreSQL outbox → Odoo | `outbox_event.id` / internal order UUID passed as Odoo's client order reference |
| Order retry/recovery | every 5 min | re-attempts failed/stuck outbox events | same as order export |
| Odoo order-status import | every 5 min | Odoo → PostgreSQL | Odoo sale order id + status timestamp |
| Order reconciliation | hourly | compares PostgreSQL vs. Odoo order state, flags drift | N/A (read-only comparison, writes to `reconciliation_result`) |
| Product reconciliation | weekly | full catalogue diff, Odoo vs. PostgreSQL | N/A (read-only comparison) |

Every task: (a) is safe to run twice on the same input (idempotent — upsert by Odoo id or
outbox event id, not blind insert), (b) records a sync-log/audit row with outcome and
timing (auditable), (c) retries with backoff on transient failure rather than dropping the
unit of work (retryable), (d) emits a metric/log line a dashboard or alert can key off of
(observable) — per rule 17. Full detail in [integration-principles.md](integration-principles.md)
and [observability.md](observability.md).

## 5. Frontend service boundaries

The frontend does not change shape (rule 20) — but as each vertical slice lands, the
*implementation* behind today's `store.ts`/`admin-store.ts` domains is replaced with calls
to a thin API-client layer, one domain at a time, matching the existing store boundaries
that the audit already found to be well-factored
([frontend-architecture.md](../current-state/frontend-architecture.md),
[roadmap.md](../current-state/roadmap.md) §4 step 4):

| Existing store domain | Future API client module (`src/lib/api/`) | Backend module it calls |
|---|---|---|
| `products.ts` + `productOverrides` (`admin-store.ts`) | `catalogue.ts` | `catalogue`, `merchandising` |
| `store.ts` → `cart` | `cart.ts` | `cart` |
| `store.ts` → `addresses`, `delivery` slot reads | `delivery.ts` | `delivery`, `customers` |
| `store.ts` → `orders`, `track` | `orders.ts` | `orders` |
| `store.ts` → `auth`, `account` | `auth.ts` | `customers` |
| `store.ts` → `promo` | `promotions.ts` | `promotions` |
| `store.ts` → `loyaltyPoints`/`loyaltyHistory` | `loyalty.ts` | `loyalty` |
| `store.ts` → `reviews` | `reviews.ts` | `reviews` |
| `admin-store.ts` → `adminAuth`, `adminSession` | `admin/auth.ts` | `admin_identity` |
| `admin-store.ts` → `staff` | `admin/staff.ts` | `admin_identity` |
| `admin-store.ts` → `banners`, `homepageSections` | `admin/content.ts` | `content`, `merchandising` |
| `admin-store.ts` → `categories` | `admin/catalogue.ts` | `merchandising` (unifying the three category sources of truth found in the audit) |
| `admin-store.ts` → `zones`, `slots` | `admin/delivery.ts` | `delivery` |
| `admin-store.ts` → `promos` | `admin/promotions.ts` | `promotions` |
| `admin-store.ts` → `settings` | `admin/settings.ts` | `content` (or a small dedicated `settings` module if it grows) |

Each client module wraps `fetch` against `/api/v1/...` (see
[api-standards.md](api-standards.md)), attaches the auth token (§
[security-boundaries.md](security-boundaries.md)), and returns typed data — replacing the
body of the corresponding `*Store` mutation/selector functions without changing their
call signatures where practical, to limit blast radius on working UI, consistent with the
existing roadmap's own stated approach.
