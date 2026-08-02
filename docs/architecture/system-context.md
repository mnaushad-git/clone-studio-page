# System Context

_C4 model, level 1 (System Context). See [target-architecture.md](target-architecture.md)
for the full rationale behind this shape._

## Actors

| Actor | Description | Interacts with |
|---|---|---|
| **Customer** | Browses/buys from the storefront, in English or Arabic (RTL). Guest or authenticated. | Customer Storefront (browser) |
| **Admin/Staff** | Manages catalogue merchandising, orders, promotions, content, staff, via `/admin/*`. Roles: owner/admin/manager/support/kitchen (existing model in `admin-store.ts`; enforcement TBD — see [security-boundaries.md](security-boundaries.md)). | Admin Portal (browser) |
| **Odoo staff/ops** | Manage product master data, pricing, tax, inventory, accounting, fulfilment directly in Odoo — outside this system's UI. | Odoo |

## System under design: "Terrific Bites Platform"

The Customer Storefront, Admin Portal, FastAPI backend, PostgreSQL, Redis, and background
workers together form one system. This is the system this document set defines.

## External systems

| System | Role | Direction | Notes |
|---|---|---|---|
| **Odoo (ERP)** | Authoritative source for product identity/SKU/variants, commercial price, tax config, inventory/ERP availability; system of record for sales orders (post-sync), invoices, accounting, ERP fulfilment status. | Bidirectional, via background workers + integration adapter only. Never reached from the browser. | Supported Odoo APIs only (§ [integration-principles.md](integration-principles.md)); no direct DB access. Odoo version/edition/hosting not yet confirmed — see open questions in [implementation-roadmap.md](implementation-roadmap.md). |
| **Payment provider** | Tokenizes and processes customer payments at checkout. | Storefront → FastAPI → provider (never raw card data through our own backend). | Provider not yet selected — GCC-relevant options noted in [implementation-roadmap.md](implementation-roadmap.md) open questions (existing UI already lists Mada/STC Pay/Apple Pay as method options). |
| **Notification provider(s)** | Email/SMS for OTP, password reset, order-status updates. | FastAPI/workers → provider. | Not yet selected — open question. |
| **Object storage** | Product images, review photos (currently base64-in-`localStorage`, a known scalability ceiling per [components.md](../current-state/components.md)). | FastAPI → storage. | Candidate: S3-compatible bucket; could reuse the already-provisioned Supabase project's storage if that project is repurposed (see [ADR-005](architecture-decision-records.md#adr-005)) rather than retired. |
| **Lovable** | Prompt-driven editor that continues to author/sync the frontend directly to this repo's branch (`AGENTS.md`). | Pushes commits to this repo. | Must remain compatible with keeping `src/` at repo root — see [target-architecture.md](target-architecture.md) §7 and open questions. |

## Context diagram

```
                      ┌───────────┐        ┌───────────┐
                      │ Customer  │        │Admin/Staff│
                      └─────┬─────┘        └─────┬─────┘
                            │ HTTPS                │ HTTPS
                            ▼                      ▼
                 ┌───────────────────────────────────────┐
                 │     Terrific Bites Platform             │
                 │  (Storefront + Admin UI, FastAPI,       │
                 │   PostgreSQL, Redis, workers)           │
                 └───┬─────────┬─────────┬─────────┬────────┘
                     │         │         │         │
             supported│  provider│ provider│  push (Lovable)
             Odoo APIs│  API     │ API     │
                     ▼         ▼         ▼         ▲
                ┌───────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
                │ Odoo  │ │Payment │ │Notif./  │ │ Lovable  │
                │ (ERP) │ │provider│ │storage  │ │ editor   │
                └───────┘ └────────┘ └─────────┘ └──────────┘
```
