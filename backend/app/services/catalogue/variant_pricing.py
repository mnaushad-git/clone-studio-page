"""Approved variant selling prices, and their reconciliation against Odoo.

The approved price of a variant is its product's `sales_price` plus every axis delta, as
recorded in data/catalogue/products.json. Odoo sells the same variant at `lst_price`, which it
computes as `list_price` plus the summed `price_extra` of the variant's attribute values.
Comparing those two figures is what proves the storefront and Odoo agree.

Pure logic: no PostgreSQL and no Odoo calls, so the importer and the worker sync share it.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.services.catalogue.odoo_import_planning import (
    CATALOGUE_DATA_DIR,
    _iter_variant_combinations,
)

_CENT = Decimal("0.01")
# Starts the error_summary of a sync run refused over prices. The health check alerts on it.
CATALOGUE_NOT_PUBLISHED = "Catalogue not published."


def to_money(value: Any) -> Decimal:
    """Through str(), because Odoo's floats and the JSON file's floats are binary."""
    return Decimal(str(value or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ExpectedVariantPrice:
    product_name: str
    variant_label: str
    sku: str
    amount: Decimal


@dataclass(frozen=True)
class PriceExtraTarget:
    """The approved delta of one attribute value on one product."""

    product_external_key: str
    product_name: str
    attribute_name: str
    value_label: str
    amount: Decimal

    @property
    def external_key(self) -> str:
        return f"{self.product_external_key}.price_extra.{self.attribute_name}.{self.value_label}"


@dataclass(frozen=True)
class OdooVariantPrice:
    odoo_variant_id: int
    amount: Decimal


@dataclass(frozen=True)
class VariantPriceRow:
    product_name: str
    variant_label: str
    sku: str
    expected: Decimal
    actual: Decimal | None
    odoo_variant_id: int | None

    @property
    def matches(self) -> bool:
        return self.actual == self.expected

    def describe(self) -> str:
        actual = "missing from Odoo" if self.actual is None else f"SAR {self.actual}"
        return (
            f"{self.product_name} / {self.variant_label} [{self.sku}]: "
            f"expected SAR {self.expected}, actual {actual}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product_name,
            "variant": self.variant_label,
            "sku": self.sku,
            "expected_price": str(self.expected),
            "actual_price": None if self.actual is None else str(self.actual),
            "odoo_variant_id": self.odoo_variant_id,
            "matches": self.matches,
        }


@dataclass(frozen=True)
class PriceReconciliation:
    rows: tuple[VariantPriceRow, ...]

    @property
    def mismatches(self) -> list[VariantPriceRow]:
        return [row for row in self.rows if not row.matches]

    @property
    def ok(self) -> bool:
        return not self.mismatches

    def summary(self) -> str:
        if self.ok:
            return f"All {len(self.rows)} variant prices match Odoo."
        details = "; ".join(row.describe() for row in self.mismatches)
        return f"{len(self.mismatches)} of {len(self.rows)} variant prices differ: {details}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "variants_checked": len(self.rows),
            "variants_matching": len(self.rows) - len(self.mismatches),
            "mismatches": [row.to_dict() for row in self.mismatches],
            "variants": [row.to_dict() for row in self.rows],
            "ok": self.ok,
        }


def load_canonical_products() -> list[dict[str, Any]]:
    path = CATALOGUE_DATA_DIR / "products.json"
    return json.loads(path.read_text(encoding="utf-8"))["products"]


def _delta_by_value(product: dict[str, Any]) -> dict[tuple[str, str], Decimal]:
    return {
        (axis["name_en"], value["label"]): to_money(value.get("delta", 0))
        for axis in (product.get("variants") or {}).get("attributes", [])
        for value in axis.get("values", [])
    }


def expected_variant_prices(products: Iterable[dict[str, Any]]) -> list[ExpectedVariantPrice]:
    expected: list[ExpectedVariantPrice] = []
    for product in products:
        if product.get("product_type") != "variant_parent":
            continue
        base = to_money(product["sales_price"])
        deltas = _delta_by_value(product)
        for _, sku, pairs in _iter_variant_combinations(product):
            expected.append(
                ExpectedVariantPrice(
                    product_name=product["name_en"],
                    variant_label=" / ".join(label for _, label in pairs),
                    sku=sku,
                    amount=base + sum((deltas[pair] for pair in pairs), Decimal(0)),
                )
            )
    return expected


def price_extra_targets(products: Iterable[dict[str, Any]]) -> list[PriceExtraTarget]:
    targets: list[PriceExtraTarget] = []
    for product in products:
        if product.get("product_type") != "variant_parent":
            continue
        for (attribute_name, value_label), amount in _delta_by_value(product).items():
            targets.append(
                PriceExtraTarget(
                    product_external_key=product["external_key"],
                    product_name=product["name_en"],
                    attribute_name=attribute_name,
                    value_label=value_label,
                    amount=amount,
                )
            )
    return targets


def reconcile_variant_prices(
    expected: Iterable[ExpectedVariantPrice],
    actual_by_sku: Mapping[str, OdooVariantPrice],
    *,
    require_all: bool,
) -> PriceReconciliation:
    """`require_all` makes a variant absent from Odoo a failure. The importer wants that, since
    it has just created every variant. The worker sync doesn't: staff may archive a product."""
    rows: list[VariantPriceRow] = []
    for item in expected:
        actual = actual_by_sku.get(item.sku)
        if actual is None and not require_all:
            continue
        rows.append(
            VariantPriceRow(
                product_name=item.product_name,
                variant_label=item.variant_label,
                sku=item.sku,
                expected=item.amount,
                actual=None if actual is None else actual.amount,
                odoo_variant_id=None if actual is None else actual.odoo_variant_id,
            )
        )
    return PriceReconciliation(rows=tuple(rows))
