"""Compares an Odoo sale.order with the storefront order it came from.

The storefront charged the customer, so its figures are the ones Odoo must reproduce. A sale
order is confirmed only when its currency, total, VAT and every line agree to two decimal
places. Anything else leaves it in draft for an operator, see LiveOdooOrderPusher.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CENT = Decimal("0.01")


def to_cents(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ExpectedLine:
    product_id: int
    quantity: int
    unit_price: float
    tax_ids: tuple[int, ...]
    name: str | None = None


@dataclass(frozen=True)
class ExpectedOrder:
    currency: str
    total: float
    tax: float
    lines: tuple[ExpectedLine, ...]


def _many2one_id(value: Any) -> Any:
    return value[0] if isinstance(value, list | tuple) and value else value


def _many2one_name(value: Any) -> Any:
    return value[1] if isinstance(value, list | tuple) and len(value) > 1 else value


def _matches(expected: ExpectedLine, actual: dict[str, Any]) -> bool:
    return (
        _many2one_id(actual.get("product_id")) == expected.product_id
        and to_cents(actual.get("product_uom_qty", 0)) == to_cents(expected.quantity)
        and to_cents(actual.get("price_unit", 0)) == to_cents(expected.unit_price)
        and sorted(actual.get("tax_ids") or []) == sorted(expected.tax_ids)
        and (expected.name is None or actual.get("name") == expected.name)
    )


def find_discrepancies(
    expected: ExpectedOrder, order: dict[str, Any], lines: list[dict[str, Any]]
) -> list[str]:
    """Every way the sale order differs from the storefront order. Empty means they agree."""
    problems: list[str] = []

    currency = _many2one_name(order.get("currency_id"))
    if currency != expected.currency:
        problems.append(f"currency: storefront {expected.currency}, Odoo {currency}")

    for label, want, got in (
        ("total", expected.total, order.get("amount_total")),
        ("VAT", expected.tax, order.get("amount_tax")),
    ):
        if got is None or to_cents(want) != to_cents(got):
            problems.append(f"{label}: storefront {to_cents(want)}, Odoo {got}")

    unmatched = list(lines)
    for line in expected.lines:
        found = next((actual for actual in unmatched if _matches(line, actual)), None)
        if found is None:
            problems.append(
                f"line missing or changed: product {line.product_id}, qty {line.quantity}, "
                f"unit price {to_cents(line.unit_price)}"
            )
        else:
            unmatched.remove(found)
    problems.extend(f"unexpected line in Odoo: id {actual.get('id')}" for actual in unmatched)
    return problems


def storefront_arithmetic_problem(
    *,
    line_amounts: list[tuple[float, int]],
    discount: float,
    delivery_fee: float,
    total: float,
) -> str | None:
    """Catches an order whose own figures don't add up, before anything reaches Odoo."""
    goods = sum((to_cents(price) * quantity for price, quantity in line_amounts), Decimal("0"))
    computed = to_cents(max(Decimal("0"), goods - to_cents(discount)) + to_cents(delivery_fee))
    if computed != to_cents(total):
        return f"lines less discount plus delivery are {computed}, order total {to_cents(total)}"
    return None
