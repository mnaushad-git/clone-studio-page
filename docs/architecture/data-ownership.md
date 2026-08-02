# Data Ownership

Every piece of data in the system has exactly one owner. The owner is the only thing
allowed to *write* the authoritative value; everything else either doesn't have the field
at all or holds a synced, read-only reflection of it (clearly named/flagged as such —
never silently overwritten by two writers).

## 1. PostgreSQL domain boundaries

One PostgreSQL database, organized into logical domains (Postgres schemas or a clear
table-prefix convention — either is acceptable; a single `public` schema with disciplined
naming is simplest for a monolith this size, formalize as an ADR if a real need for
schema-level separation emerges):

| Domain | Representative tables | Module owner (§[component-view.md](component-view.md)) |
|---|---|---|
| `catalogue` | `product`, `product_variant`, `product_price_cache`, `product_availability_cache` | `catalogue` |
| `merchandising` | `product_merchandising` (display order, badges, marketing copy), `homepage_section`, `banner` | `merchandising`, `content` |
| `content` | `moment`, `recipient`, `content_page` | `content` |
| `commerce` | `cart`, `cart_item`, `checkout_session`, `payment_reference` | `cart`, `checkout` |
| `orders` | `order`, `order_item`, `order_status_history`, `outbox_event` | `orders`, `outbox` |
| `identity` | `customer`, `customer_session`, `admin_staff`, `admin_role`, `admin_session` | `customers`, `admin_identity` |
| `promotions` / `delivery` / `reviews` / `loyalty` | `promo_code`, `promo_redemption`, `delivery_zone`, `delivery_slot`, `review`, `loyalty_ledger` | respective modules |
| `integration` | `sync_checkpoint`, `sync_audit_log`, `reconciliation_result` | `catalogue`/`orders` workers, shared |

## 2. Odoo-owned fields (authoritative in Odoo; PostgreSQL holds a synced cache only)

| Field / concept | Odoo model (typical) | PostgreSQL representation |
|---|---|---|
| Product and variant identity | `product.template` / `product.product` | `product.odoo_product_id`, `product_variant.odoo_variant_id` — foreign identity, not regenerated locally |
| SKU / internal reference | `product.product.default_code` | `product.sku` (synced, read-only from the API's perspective) |
| Base commercial price | `product.template.list_price` (or pricelist) | `product_price_cache.base_price`, with `synced_at` |
| Tax configuration | `account.tax` mapping on the product | `product.tax_class` / `tax_rate_cache` |
| Product active status | `product.template.active` | `product.is_active` |
| Inventory / ERP availability | `stock.quant` / on-hand & reserved qty | `product_availability_cache.qty_available`, `synced_at` |
| Sales orders (after synchronisation) | `sale.order` | `order.odoo_sale_order_id`, `order.sync_status`, `order_status_history` entries fed by status import |
| Invoices | `account.move` | Not stored beyond a reference id/link (`order.odoo_invoice_id`) — invoice content itself is not duplicated into PostgreSQL |
| Accounting | Odoo accounting modules | Not represented in PostgreSQL at all |
| ERP fulfilment status | `stock.picking` / delivery state on the sale order | `order.fulfilment_status` (synced reflection) |

**Rule:** no PostgreSQL write path may set any of the above fields directly from an
Admin Portal or Storefront request. They are only ever written by the product-sync or
order-status-import workers. If the API needs to *display* one of these values, it reads
the cached column; it never accepts it as user input.

## 3. PostgreSQL/Admin-owned fields (authoritative in PostgreSQL; Odoo never sees these)

| Field / concept | Table |
|---|---|
| Homepage sections | `homepage_section` |
| Hero banners | `banner` |
| Product merchandising (display order, badges, marketing description) | `product_merchandising` |
| Product display order | `product_merchandising.display_order` |
| Marketing descriptions and badges | `product_merchandising.marketing_description`, `product_merchandising.badges` |
| Moments | `moment` |
| Recipients | `recipient` |
| Content pages | `content_page` |
| Customer sessions | `customer_session` |
| Carts | `cart`, `cart_item` |
| Checkout state | `checkout_session` |
| Payment references | `payment_reference` (opaque token from the payment provider — never raw card data, per rule 22/PCI scope, see [security-boundaries.md](security-boundaries.md)) |
| Storefront order before Odoo synchronisation | `order` (status `pending_sync`) |
| Integration queues | `outbox_event` |
| Sync checkpoints | `sync_checkpoint` |
| Audit records | `sync_audit_log`, plus admin-mutation audit entries (§[observability.md](observability.md)) |
| Reconciliation results | `reconciliation_result` |

Additionally, staff/admin identity, RBAC roles, promo codes, delivery zones/slots,
reviews, and the loyalty ledger are PostgreSQL/Admin-owned outright — Odoo has no concept
of them.

## 4. The product record, concretely

Because "product" is the one entity split across both owners, its shape is spelled out
explicitly (this is what rule 19 — "Odoo-controlled commercial fields must be separated
from Admin Portal-controlled merchandising fields" — means in schema terms):

```
product                          product_merchandising
├── id (internal PK)             ├── product_id (FK → product.id)
├── odoo_product_id  ┐            ├── display_order
├── sku               │ Odoo-     ├── badges (e.g. "New", "Bestseller")
├── name               │ owned,    ├── marketing_description_en / _ar
├── base_price          │ synced    ├── homepage_featured (bool)
├── tax_class            │ from     ├── visible_override (admin can hide without
├── is_active              │ Odoo,   │    touching Odoo's active flag)
├── qty_available            │ never  └── updated_by_admin_id / updated_at
├── synced_at                ┘ hand-
└── sync_status                edited
```

A catalogue API response is the join of both tables. The admin "edit product" screen
writes only to `product_merchandising`; it never exposes an editable field for anything in
the left column — those change only when the next Odoo sync runs. This directly resolves
the audit's finding that admin `productOverrides` today conflates commercial fields
(price, stock) with merchandising fields (visibility, name, description) in one
undifferentiated blob ([mock-data.md](../current-state/mock-data.md)).

## 5. Ownership transition for orders

An order has exactly one authoritative owner at any point in time, but that owner changes
over the order's lifecycle:

1. **Created → `pending_sync`**: PostgreSQL is authoritative (customer just checked out;
   Odoo doesn't know about it yet).
2. **Exported → `synced`**: once the order-export worker confirms Odoo accepted the sales
   order, Odoo becomes authoritative for fulfilment/invoice/accounting status. PostgreSQL
   stores a synced reflection (`order.fulfilment_status`, `order.odoo_invoice_id`, status
   history rows) updated by the status-import worker — never edited directly by an admin
   action in a way that diverges from Odoo.
3. **Admin actions that remain PostgreSQL-native** even post-sync: internal notes, customer
   service annotations, and anything explicitly out of Odoo's model — these get their own
   columns/tables, never overloaded onto the synced fields.

## 6. Weekly/hourly reconciliation exists because of this split

Because two systems each hold a partial view, drift is possible (a worker failure, a
manual Odoo-side edit, a network partition mid-sync). Reconciliation jobs
(§[component-view.md](component-view.md) §4) don't reconcile by guessing — they compare
the synced-from-Odoo fields against Odoo's current state and flag/report drift into
`reconciliation_result` for a human to act on. Reconciliation never auto-resolves a
conflict silently; see [integration-principles.md](integration-principles.md).
