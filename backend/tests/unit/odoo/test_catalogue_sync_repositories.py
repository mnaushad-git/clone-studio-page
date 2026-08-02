"""Unit tests for the new Odoo repository methods backing the Odoo -> PostgreSQL
catalogue pull sync — everything here uses FakeTransport, no network, no DB."""

from __future__ import annotations

import pytest

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooRemoteError
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.pricelists import OdooPricelistRepository
from app.integrations.odoo.repositories.product_images import OdooProductImageRepository
from app.integrations.odoo.repositories.products import OdooProductRepository
from app.integrations.odoo.repositories.stock import OdooStockRepository
from tests.unit.odoo.conftest import FakeTransport


def test_iter_all_categories_includes_write_date_and_domain(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.category", "search_read"),
        [
            {
                "id": 5,
                "name": "Cakes",
                "display_name": "Cakes",
                "parent_id": False,
                "complete_name": "Cakes",
                "write_date": "2026-07-30 10:00:00",
            }
        ],
    )
    repo = OdooCategoryRepository(authenticated_client)

    records = list(
        repo.iter_all_categories(
            domain=[["write_date", ">=", "2026-07-01 00:00:00"]], max_records=100
        )
    )

    assert records == [
        {
            "id": 5,
            "name": "Cakes",
            "display_name": "Cakes",
            "parent_id": False,
            "complete_name": "Cakes",
            "write_date": "2026-07-30 10:00:00",
        }
    ]
    call = transport.calls[-1]
    assert call.args[3] == "product.category"
    assert call.args[5][0] == [["write_date", ">=", "2026-07-01 00:00:00"]]
    assert "write_date" in call.args[6]["fields"]


def test_iter_all_templates_with_domain_uses_sync_fields(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search_read"), [])
    repo = OdooProductRepository(authenticated_client)

    list(repo.iter_all_templates(domain=[], max_records=100))

    call = transport.calls[-1]
    assert "write_date" in call.args[6]["fields"]


def test_iter_all_templates_without_domain_uses_plain_fields(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search_read"), [])
    repo = OdooProductRepository(authenticated_client)

    list(repo.iter_all_templates(max_records=100))

    call = transport.calls[-1]
    assert "write_date" not in call.args[6]["fields"]


def test_iter_all_variants_orders_by_template(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.product", "search_read"), [])
    repo = OdooProductRepository(authenticated_client)

    list(repo.iter_all_variants(max_records=100))

    call = transport.calls[-1]
    assert call.args[6]["order"] == "product_tmpl_id"
    assert "write_date" in call.args[6]["fields"]


def test_product_image_repository_uses_small_batch_size(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.image", "search_read"), [])
    repo = OdooProductImageRepository(authenticated_client)

    list(repo.iter_for_templates([1, 2], max_records=100))

    call = transport.calls[-1]
    assert call.args[3] == "product.image"
    assert call.args[5][0] == [["product_tmpl_id", "in", [1, 2]]]
    assert call.args[6]["limit"] == 20


def test_product_image_repository_empty_template_ids_makes_no_call(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    repo = OdooProductImageRepository(authenticated_client)

    assert list(repo.iter_for_templates([], max_records=100)) == []
    assert not any(c.method == "execute_kw" for c in transport.calls)


def test_stock_get_available_quantities_sums_quantity_minus_reserved(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "stock.quant", "read_group"),
        [{"product_id": [10, "Cupcake"], "quantity": 15.0, "reserved_quantity": 3.0}],
    )
    repo = OdooStockRepository(authenticated_client)

    result = repo.get_available_quantities([10], location_id=None)

    assert result == {10: 12.0}
    call = transport.calls[-1]
    assert call.args[4] == "read_group"
    assert call.args[5][0] == [["product_id", "in", [10]], ["location_id.usage", "=", "internal"]]


def test_stock_get_available_quantities_filters_by_location_when_given(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "stock.quant", "read_group"), [])
    repo = OdooStockRepository(authenticated_client)

    repo.get_available_quantities([10], location_id=99)

    call = transport.calls[-1]
    assert call.args[5][0] == [["product_id", "in", [10]], ["location_id", "=", 99]]


def test_stock_get_available_quantities_empty_products_makes_no_call(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    repo = OdooStockRepository(authenticated_client)

    assert repo.get_available_quantities([]) == {}
    assert not any(c.method == "execute_kw" for c in transport.calls)


def test_stock_get_available_quantities_propagates_model_not_installed(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    """The real connected Odoo instance has no Inventory app installed — stock.quant
    reports "model not installed" — this must surface as a real exception the sync
    service's own try/except is responsible for catching, not something this
    repository silently swallows."""
    transport.queue(
        ("execute_kw", "stock.quant", "read_group"),
        OdooRemoteError("Object stock.quant doesn't exist", context={}),
    )
    repo = OdooStockRepository(authenticated_client)

    with pytest.raises(OdooRemoteError):
        repo.get_available_quantities([10])


def test_pricelist_iter_items_scopes_to_pricelist_and_extra_domain(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.pricelist.item", "search_read"), [])
    repo = OdooPricelistRepository(authenticated_client)

    list(
        repo.iter_items_for_pricelist(
            7, domain=[["write_date", ">=", "2026-07-01 00:00:00"]], max_records=50
        )
    )

    call = transport.calls[-1]
    assert call.args[3] == "product.pricelist.item"
    assert call.args[5][0] == [
        ["pricelist_id", "=", 7],
        ["write_date", ">=", "2026-07-01 00:00:00"],
    ]
