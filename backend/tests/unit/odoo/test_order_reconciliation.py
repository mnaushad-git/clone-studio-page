"""The comparison that decides whether a sale order is confirmed. Pure, no Odoo involved."""

from __future__ import annotations

from typing import Any

import pytest

from app.integrations.odoo.order_reconciliation import (
    ExpectedLine,
    ExpectedOrder,
    find_discrepancies,
    storefront_arithmetic_problem,
    to_cents,
)


def _expected(**overrides: Any) -> ExpectedOrder:
    values: dict[str, Any] = {
        "currency": "SAR",
        "total": 915.0,
        "tax": 119.35,
        "lines": (
            ExpectedLine(10, 2, 450.0, (5,), "Cake\nInscription: Happy Birthday"),
            ExpectedLine(90, 1, 15.0, (5,), "Delivery"),
        ),
    }
    values.update(overrides)
    return ExpectedOrder(**values)


def _order(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "amount_tax": 119.35,
        "amount_total": 915.0,
        "currency_id": [147, "SAR"],
    }
    values.update(overrides)
    return values


def _lines() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "product_id": [10, "Cake"],
            "product_uom_qty": 2.0,
            "price_unit": 450.0,
            "tax_ids": [5],
            "name": "Cake\nInscription: Happy Birthday",
        },
        {
            "id": 2,
            "product_id": [90, "Delivery"],
            "product_uom_qty": 1.0,
            "price_unit": 15.0,
            "tax_ids": [5],
            "name": "Delivery",
        },
    ]


def test_a_matching_order_has_no_discrepancies() -> None:
    assert find_discrepancies(_expected(), _order(), _lines()) == []


def test_line_order_does_not_matter() -> None:
    assert find_discrepancies(_expected(), _order(), list(reversed(_lines()))) == []


@pytest.mark.parametrize(
    ("overrides", "label"),
    [
        ({"amount_total": 1035.0}, "total"),
        ({"amount_total": 915.01}, "total"),
        ({"amount_tax": 135.0}, "VAT"),
        ({"currency_id": [1, "USD"]}, "currency"),
    ],
)
def test_header_differences_are_reported(overrides: dict[str, Any], label: str) -> None:
    problems = find_discrepancies(_expected(), _order(**overrides), _lines())
    assert any(problem.startswith(label) for problem in problems)


def test_a_difference_below_half_a_cent_is_not_a_difference() -> None:
    assert find_discrepancies(_expected(), _order(amount_total=915.0000001), _lines()) == []


@pytest.mark.parametrize(
    "change",
    [
        {"product_uom_qty": 3.0},
        {"price_unit": 451.0},
        {"tax_ids": [6]},
        {"tax_ids": []},
        {"name": "Cake"},
        {"product_id": [11, "Other Cake"]},
    ],
)
def test_a_changed_line_is_reported(change: dict[str, Any]) -> None:
    lines = _lines()
    lines[0] = {**lines[0], **change}
    problems = find_discrepancies(_expected(), _order(), lines)
    assert any("line" in problem for problem in problems)


def test_an_extra_odoo_line_is_reported() -> None:
    extra = {"id": 3, "product_id": [12, "x"], "product_uom_qty": 1, "price_unit": 1, "tax_ids": []}
    problems = find_discrepancies(_expected(), _order(), [*_lines(), extra])
    assert any("unexpected line" in problem for problem in problems)


def test_a_zero_tax_delivery_line_is_compared_against_no_tax() -> None:
    """The alternative classification finance might choose must also reconcile."""
    expected = _expected(lines=(ExpectedLine(90, 1, 15.0, (), "Delivery"),))
    lines = [{**_lines()[1], "tax_ids": []}]
    assert find_discrepancies(expected, _order(), lines) == []


def test_an_expected_line_without_a_name_ignores_the_odoo_description() -> None:
    expected = _expected(lines=(ExpectedLine(90, 1, 15.0, (5,)),))
    assert find_discrepancies(expected, _order(), [_lines()[1]]) == []


@pytest.mark.parametrize(
    ("value", "cents"),
    [(1.005, "1.01"), (2.675, "2.68"), (900, "900.00"), (119.3478, "119.35"), ("0.1", "0.10")],
)
def test_amounts_round_half_up_to_two_places(value: Any, cents: str) -> None:
    assert str(to_cents(value)) == cents


def test_consistent_storefront_arithmetic_passes() -> None:
    assert (
        storefront_arithmetic_problem(
            line_amounts=[(450.0, 2)], discount=45.0, delivery_fee=15.0, total=870.0
        )
        is None
    )


def test_inconsistent_storefront_arithmetic_is_described() -> None:
    problem = storefront_arithmetic_problem(
        line_amounts=[(450.0, 2)], discount=0.0, delivery_fee=15.0, total=914.0
    )
    assert problem is not None
    assert "915.00" in problem
