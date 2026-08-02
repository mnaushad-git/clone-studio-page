from __future__ import annotations

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.models import AvailabilityStatus
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.currencies import OdooCurrencyRepository
from app.integrations.odoo.repositories.metadata import MetadataRepository
from app.integrations.odoo.repositories.pricelists import OdooPricelistRepository
from app.integrations.odoo.repositories.products import OdooProductRepository
from app.integrations.odoo.repositories.stock import OdooStockRepository
from app.integrations.odoo.repositories.taxes import OdooTaxRepository
from app.integrations.odoo.repositories.units_of_measure import OdooUomRepository
from tests.unit.odoo.conftest import FakeTransport


def test_model_availability_unavailable_when_model_missing(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model", "search_count"), 0)
    repo = MetadataRepository(authenticated_client)

    availability = repo.model_availability("some.nonexistent.model")

    assert availability.status == AvailabilityStatus.UNAVAILABLE


def test_model_availability_no_access_when_read_denied(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model", "search_count"), 1)
    transport.queue(("execute_kw", "stock.quant", "check_access_rights"), False)
    repo = MetadataRepository(authenticated_client)

    availability = repo.model_availability("stock.quant")

    assert availability.status == AvailabilityStatus.NO_ACCESS


def test_model_availability_available_when_installed_and_readable(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model", "search_count"), 1)
    transport.queue(("execute_kw", "product.template", "check_access_rights"), True)
    repo = MetadataRepository(authenticated_client)

    availability = repo.model_availability("product.template")

    assert availability.status == AvailabilityStatus.AVAILABLE


def test_get_companies_parses_currency_tuple(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "res.company", "search_read"),
        [{"id": 1, "name": "Terrific Bites LLC", "currency_id": [12, "SAR"]}],
    )
    repo = MetadataRepository(authenticated_client)

    companies = repo.get_companies()

    assert companies[0].currency_id == 12
    assert companies[0].currency_name == "SAR"


def test_category_repository_find_by_name(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.category", "search_read"), [{"id": 5, "name": "Cupcakes"}]
    )

    matches = OdooCategoryRepository(authenticated_client).find_by_name("Cupcakes")

    assert matches[0]["id"] == 5


def test_product_repository_find_by_default_code(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.template", "search_read"), [{"id": 9, "default_code": "TB-CUP-001"}]
    )

    matches = OdooProductRepository(authenticated_client).find_templates_by_default_code(
        "TB-CUP-001"
    )

    assert matches[0]["id"] == 9


def test_product_repository_iter_all_templates_is_bounded(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search_read"), [{"id": 1}, {"id": 2}])

    records = list(OdooProductRepository(authenticated_client).iter_all_templates(max_records=2))

    assert len(records) == 2


def test_tax_repository_list_sale_taxes(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "account.tax", "search_read"), [{"id": 1, "name": "VAT 15%", "amount": 15.0}]
    )

    taxes = OdooTaxRepository(authenticated_client).list_sale_taxes()

    assert taxes[0]["amount"] == 15.0


def test_uom_repository_list_reference_units(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "uom.uom", "search_read"), [{"id": 1, "name": "Units"}])

    units = OdooUomRepository(authenticated_client).list_reference_units()

    assert units[0]["name"] == "Units"


def test_currency_repository_find_by_code(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "res.currency", "search_read"), [{"id": 12, "name": "SAR"}])

    matches = OdooCurrencyRepository(authenticated_client).find_by_code("SAR")

    assert matches[0]["id"] == 12


def test_pricelist_repository_list_active(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.pricelist", "search_read"), [{"id": 1, "name": "Public Pricelist"}]
    )

    pricelists = OdooPricelistRepository(authenticated_client).list_active_pricelists()

    assert pricelists[0]["name"] == "Public Pricelist"


def test_stock_repository_list_warehouses(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "stock.warehouse", "search_read"), [{"id": 1, "name": "Main Warehouse"}]
    )

    warehouses = OdooStockRepository(authenticated_client).list_warehouses()

    assert warehouses[0]["name"] == "Main Warehouse"
