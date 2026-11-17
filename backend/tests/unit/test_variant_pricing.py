from __future__ import annotations

from decimal import Decimal

from app.services.catalogue.variant_pricing import (
    OdooVariantPrice,
    expected_variant_prices,
    load_canonical_products,
    price_extra_targets,
    reconcile_variant_prices,
    to_money,
)

D = Decimal


def _expected() -> list:
    return expected_variant_prices(load_canonical_products())


def test_catalogue_has_the_approved_variant_shape() -> None:
    expected = _expected()
    bases = {p["name_en"]: to_money(p["sales_price"]) for p in load_canonical_products()}

    assert len(load_canonical_products()) == 26
    assert len(expected) == 55
    assert len({row.sku for row in expected}) == 55
    assert sum(1 for row in expected if row.amount != bases[row.product_name]) == 28


def test_berry_truffle_large_box_is_approved_at_14_38() -> None:
    by_sku = {row.sku: row for row in _expected()}

    assert by_sku["TB-CHO-009-LARGEBOX"].amount == D("14.38")
    assert by_sku["TB-CHO-009-SMALLBOX"].amount == D("7.99")


def test_two_axis_prices_compose_additively() -> None:
    products = [
        {
            "external_key": "p",
            "sku": "X",
            "name_en": "Cake",
            "sales_price": 10.10,
            "product_type": "variant_parent",
            "variants": {
                "attributes": [
                    {
                        "name_en": "Size",
                        "values": [{"label": "S", "delta": 0}, {"label": "L", "delta": 5.05}],
                    },
                    {
                        "name_en": "Flavor",
                        "values": [{"label": "A", "delta": 0}, {"label": "B", "delta": 0.10}],
                    },
                ]
            },
        }
    ]

    prices = {row.sku: row.amount for row in expected_variant_prices(products)}

    assert prices == {
        "X-S-A": D("10.10"),
        "X-S-B": D("10.20"),
        "X-L-A": D("15.15"),
        "X-L-B": D("15.25"),
    }
    assert len(price_extra_targets(products)) == 4


def _one_expected() -> list:
    return [row for row in _expected() if row.sku == "TB-CHO-009-LARGEBOX"]


def test_matching_prices_pass() -> None:
    result = reconcile_variant_prices(
        _one_expected(),
        {"TB-CHO-009-LARGEBOX": OdooVariantPrice(5, D("14.38"))},
        require_all=True,
    )

    assert result.ok
    assert result.to_dict()["variants_matching"] == 1


def test_a_difference_of_one_cent_fails_and_names_the_variant() -> None:
    result = reconcile_variant_prices(
        _one_expected(),
        {"TB-CHO-009-LARGEBOX": OdooVariantPrice(5, D("14.37"))},
        require_all=True,
    )

    assert not result.ok
    message = result.summary()
    for part in ("Berry Truffle", "LARGE BOX", "14.38", "14.37"):
        assert part in message


def test_missing_variant_fails_only_when_all_are_required() -> None:
    assert not reconcile_variant_prices(_one_expected(), {}, require_all=True).ok
    assert reconcile_variant_prices(_one_expected(), {}, require_all=False).ok


def test_float_noise_from_odoo_does_not_count_as_a_difference() -> None:
    assert to_money(14.380000000000001) == D("14.38")
    assert to_money(False) == D("0.00")
