# Order financials: storefront to Odoo

How a storefront order becomes an Odoo sale order with the same money. For anyone changing
pricing, tax or the order push.

**The VAT treatment and delivery tax below are proposed rules awaiting client finance approval.**
Until then, `DEPLOYMENT_STAGE=live` refuses to start: it requires `FINANCE_RULES_APPROVED=true`.

## The proposed rules

| Rule | Value | Where |
|---|---|---|
| Currency | SAR | `orders.currency`, SAR pricelist in Odoo |
| VAT rate | 15% | `CHECKOUT_TAX_RATE_PERCENT`, Odoo tax amount |
| Prices include VAT | Yes | Storefront prices are unchanged. VAT is extracted, never added |
| Delivery fee includes VAT | Yes | `CHECKOUT_DELIVERY_VAT_APPLIES` |
| Rounding | Whole order, to 2 decimals | Odoo `round_globally`, one VAT figure in the storefront |

VAT on an order is `gross x 15 / 115`, where gross is goods less discount, plus delivery when the
fee is taxable.

If finance rules that delivery carries no VAT, set `CHECKOUT_DELIVERY_VAT_APPLIES=false`. The
storefront's VAT figure and the Odoo delivery line then both change together.

## How an order is written to Odoo

| Storefront | Odoo sale order line |
|---|---|
| Product | Variant, quantity and unit price exactly as sold. The description holds the options and inscription |
| Discount (whole order) | One negative line on `TB-PROMO-DISCOUNT`. Product prices stay as sold |
| Delivery fee | One line on `TB-DELIVERY-FEE`, or no line when delivery is free |

Every line sets its tax explicitly, so a product's own tax setting can't change what was charged.

## Failing safely

1. Before contacting Odoo, the order's own figures must add up. If they don't, nothing is sent.
2. The pusher refuses to run unless Odoo has exactly one active SAR pricelist and exactly one
   active price-included sale tax at the configured rate.
3. After creating the sale order, it reads the order back. Currency, total, VAT and every line
   must match to two decimal places.
4. On any difference the sale order **stays in draft**, the push is recorded as failed with the
   exact difference in `order_outbox_events.last_error`, and the outbox retries, then
   dead-letters it for an operator. Tax is never removed to make totals agree.

The same comparison runs when a retry finds an existing order. Comparison lives in
[order_reconciliation.py](../../backend/app/integrations/odoo/order_reconciliation.py).

## Odoo setup

[bootstrap.py](../../deploy/odoo/bootstrap.py) sets all of this up and is safe to rerun. It loads
the Saudi chart of accounts (`l10n_sa`), marks the company's 15% sale tax as price-included, and
creates the SAR pricelist and the two service products. The `terrific_order_sync` addon depends
on `l10n_sa`, so installing the addon installs it.

Bootstrap refuses to replace a chart of accounts on a database that already has accounting
entries. That case needs an accountant, not a script.

Tax registration, ZATCA e-invoicing and the invoicing flow are not configured here.

## Proving it

```bash
backend/.venv/Scripts/python deploy/native/native_stack.py verify-financials
```

This places real orders through the API and worker into the isolated Odoo: delivery charged and
free, multiple quantities, mixed variants, percentage and fixed discounts, and an inscription.
It then shows a VAT difference being held in draft and recovering once corrected. See
[native-integration.md](../deployment/native-integration.md).
