"""Integration tests for the Odoo -> PostgreSQL catalogue pull sync, run against real
PostgreSQL (see tests/conftest.py's db_session fixture). Odoo itself is never real
here — _connect_readonly() is monkeypatched per test, exactly like the push-direction
service's own tests (test_odoo_import_service.py), so these never require a live Odoo
instance or a real network call.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooRemoteError
from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.services.catalogue import odoo_catalogue_sync_service as service_module
from app.services.catalogue.odoo_catalogue_sync_service import OdooCatalogueSyncService
from tests.integration.catalogue_factories import make_category, make_product
from tests.unit.odoo.conftest import FakeTransport, make_config


def _table_count(session: Session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608


def _fake_connected_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    categories: list[dict[str, Any]] | None = None,
    templates: list[dict[str, Any]] | None = None,
    variants: list[dict[str, Any]] | None = None,
    images: list[dict[str, Any]] | None = None,
    stock: Any = None,
    template_attribute_values: list[dict[str, Any]] | None = None,
    attribute_values: list[dict[str, Any]] | None = None,
) -> FakeTransport:
    """Wires _connect_readonly() to return an authenticated OdooClient over a
    FakeTransport pre-loaded with responses for every model the sync reads. Passing
    `stock` as an exception instance queues a failure (e.g. "model not installed")
    instead of a quantity result. `template_attribute_values`/`attribute_values` back
    the two bulk `read()` calls sync_variants makes only when at least one variant
    record carries `product_template_attribute_value_ids` — omit them for tests with
    no attribute data (existing tests never queue these keys and never call them).
    """
    config = make_config()
    transport = FakeTransport()
    transport.queue(("common", "version"), {"server_version": "19.0-test"})
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.category", "search_read"), categories or [])
    transport.queue(("execute_kw", "product.template", "search_read"), templates or [])
    transport.queue(("execute_kw", "product.product", "search_read"), variants or [])
    transport.queue(("execute_kw", "product.image", "search_read"), images or [])
    transport.queue(("execute_kw", "stock.quant", "read_group"), stock if stock is not None else [])
    if template_attribute_values is not None:
        transport.queue(
            ("execute_kw", "product.template.attribute.value", "read"), template_attribute_values
        )
    if attribute_values is not None:
        transport.queue(("execute_kw", "product.attribute.value", "read"), attribute_values)

    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()

    monkeypatch.setattr(service_module, "_connect_readonly", lambda settings: (client, None))
    return transport


def _category_record(odoo_id: int, name: str) -> dict[str, Any]:
    return {
        "id": odoo_id,
        "name": name,
        "display_name": name,
        "parent_id": False,
        "complete_name": name,
        "write_date": "2026-07-30 10:00:00",
    }


def _template_record(
    odoo_id: int, name: str, *, categ_id: int, sku: str | None = None
) -> dict[str, Any]:
    return {
        "id": odoo_id,
        "name": name,
        "display_name": name,
        "default_code": sku,
        "categ_id": [categ_id, "Category"],
        "list_price": 25.5,
        "currency_id": [1, "SAR"],
        "taxes_id": [],
        "active": True,
        "sale_ok": True,
        "type": "consu",
        "uom_id": [1, "Units"],
        "description_sale": "A description",
        "image_1920": False,
        "write_date": "2026-07-30 10:00:00",
    }


def _variant_record(
    odoo_id: int,
    tmpl_id: int,
    name: str,
    *,
    sku: str | None = None,
    ptav_ids: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "id": odoo_id,
        "name": name,
        "default_code": sku,
        "product_tmpl_id": [tmpl_id, name],
        "active": True,
        "write_date": "2026-07-30 10:00:00",
        "product_template_attribute_value_ids": ptav_ids or [],
    }


def _ptav_record(odoo_id: int, value_id: int, *, price_extra: float = 0.0) -> dict[str, Any]:
    """product.template.attribute.value — the per-template-per-value join row."""
    return {
        "id": odoo_id,
        "product_attribute_value_id": [value_id, "Value"],
        "price_extra": price_extra,
    }


def _attribute_value_record(
    odoo_id: int, name: str, *, attribute_id: int, attribute_name: str
) -> dict[str, Any]:
    return {"id": odoo_id, "name": name, "attribute_id": [attribute_id, attribute_name]}


# -- categories --------------------------------------------------------------------------


def test_sync_creates_new_category_when_no_match_exists(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(monkeypatch, categories=[_category_record(501, "Cupcakes")])
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-1", full_resync=True
    )

    assert run.status == "SUCCEEDED"
    category = (
        db_session.query(CatalogueCategory).filter(CatalogueCategory.odoo_category_id == 501).one()
    )
    assert category.name_en == "Cupcakes"
    assert category.source_system == "odoo"


def test_sync_adopts_existing_seed_category_by_name_match(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = make_category(db_session, name_en="Cupcakes")
    db_session.commit()
    _fake_connected_client(monkeypatch, categories=[_category_record(502, "Cupcakes")])
    service = OdooCatalogueSyncService(db_session)

    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-2", full_resync=True
    )

    db_session.refresh(existing)
    assert existing.odoo_category_id == 502
    assert _table_count(db_session, "catalogue_categories") == 1


def test_sync_matches_by_odoo_id_on_second_run_not_duplicated(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(monkeypatch, categories=[_category_record(503, "Chocolates")])
    service = OdooCatalogueSyncService(db_session)
    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-3a", full_resync=True
    )

    _fake_connected_client(monkeypatch, categories=[_category_record(503, "Chocolates Renamed")])
    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-3b", full_resync=True
    )

    assert _table_count(db_session, "catalogue_categories") == 1
    category = (
        db_session.query(CatalogueCategory).filter(CatalogueCategory.odoo_category_id == 503).one()
    )
    assert category.name_en == "Chocolates Renamed"


# -- products --------------------------------------------------------------------------


def test_sync_products_fails_item_when_category_not_resolved(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No category queued at all — the product references categ_id 999, which the
    # category phase never sees, so it can never be resolved this run.
    _fake_connected_client(
        monkeypatch, templates=[_template_record(701, "Mystery Cake", categ_id=999, sku="MYST-1")]
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-4", full_resync=True
    )

    assert run.status == "FAILED"
    assert _table_count(db_session, "catalogue_products") == 0
    items = list(
        db_session.execute(
            text(
                "SELECT error_code FROM odoo_catalogue_sync_items "
                "WHERE entity_type = 'PRODUCT_TEMPLATE'"
            )
        )
    )
    assert items and items[0][0] == "ValueError"


def test_sync_products_refuses_sku_collision_with_different_odoo_template(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = make_product(db_session, sku="SHARED-SKU", odoo_product_template_id=111)
    db_session.commit()
    _fake_connected_client(
        monkeypatch,
        categories=[_category_record(801, "Cakes")],
        templates=[_template_record(222, "Different Cake", categ_id=801, sku="SHARED-SKU")],
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-5", full_resync=True
    )

    assert run.status in ("FAILED", "PARTIALLY_COMPLETED")
    db_session.refresh(existing)
    assert existing.odoo_product_template_id == 111  # untouched
    assert _table_count(db_session, "catalogue_products") == 1


def test_sync_creates_product_with_merchandising_row(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(
        monkeypatch,
        categories=[_category_record(802, "Cakes")],
        templates=[_template_record(223, "Red Velvet", categ_id=802, sku="RV-1")],
        variants=[_variant_record(9001, 223, "Red Velvet", sku="RV-1")],
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-6", full_resync=True
    )

    assert run.status == "SUCCEEDED"
    product = (
        db_session.query(CatalogueProduct)
        .filter(CatalogueProduct.odoo_product_template_id == 223)
        .one()
    )
    merch_count = db_session.execute(
        text("SELECT count(*) FROM catalogue_product_merchandising WHERE product_id = :pid"),
        {"pid": str(product.id)},
    ).scalar_one()
    assert merch_count == 1
    variant_count = db_session.execute(
        text("SELECT count(*) FROM catalogue_product_variants WHERE product_id = :pid"),
        {"pid": str(product.id)},
    ).scalar_one()
    assert variant_count == 1
    price_count = db_session.execute(
        text("SELECT count(*) FROM catalogue_product_prices")
    ).scalar_one()
    assert price_count == 1


# -- variant attributes (pull direction of the Odoo attribute/variant model) ---------------


def test_sync_resolves_attribute_combination_and_adds_price_extra(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand-new Odoo product with a real Size x Flavor attribute structure (2
    template.attribute.line's worth of combinations) flows into Postgres with correct
    catalogue_product_attribute_values rows and a price reflecting list_price +
    price_extra — the exact gap this pull-sync extension closes.
    """
    _fake_connected_client(
        monkeypatch,
        categories=[_category_record(701, "Cakes")],
        templates=[_template_record(310, "Layer Cake", categ_id=701, sku="LC-1")],
        variants=[
            _variant_record(410, 310, "Layer Cake (9 Inch, Vanilla)", sku="LC-1-9V", ptav_ids=[1, 2]),
        ],
        template_attribute_values=[
            _ptav_record(1, 101, price_extra=20.0),
            _ptav_record(2, 102, price_extra=0.0),
        ],
        attribute_values=[
            _attribute_value_record(101, "9 Inch", attribute_id=11, attribute_name="Size"),
            _attribute_value_record(102, "Vanilla", attribute_id=12, attribute_name="Flavor"),
        ],
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-attr-1", full_resync=True
    )

    assert run.status == "SUCCEEDED"
    variant = (
        db_session.query(CatalogueProductVariant)
        .filter(CatalogueProductVariant.odoo_product_variant_id == 410)
        .one()
    )
    rows = {
        r.attribute_code: r
        for r in db_session.execute(
            text(
                "SELECT attribute_code, attribute_name_en, value_label_en, odoo_attribute_id, "
                "odoo_attribute_value_id FROM catalogue_product_attribute_values "
                "WHERE variant_id = :vid"
            ),
            {"vid": str(variant.id)},
        ).mappings()
    }
    assert rows["size"]["attribute_name_en"] == "Size"
    assert rows["size"]["value_label_en"] == "9 Inch"
    assert rows["size"]["odoo_attribute_id"] == 11
    assert rows["flavor"]["value_label_en"] == "Vanilla"

    price = db_session.execute(
        text(
            "SELECT amount FROM catalogue_product_prices WHERE product_variant_id = :vid"
        ),
        {"vid": str(variant.id)},
    ).scalar_one()
    assert float(price) == 25.5 + 20.0  # _template_record's list_price + this combo's price_extra


def test_sync_reuses_attribute_code_for_unrecognized_attribute_name_across_products(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An Odoo attribute whose name matches no known heuristic ("Topping") gets
    whatever code the ladder assigns on first encounter — and every later variant
    referencing that same odoo_attribute_id reuses it exactly, even when that later
    variant's own positional slots are all still open (which would otherwise make
    positional fallback assign a different, wrong code).
    """
    _fake_connected_client(
        monkeypatch,
        categories=[_category_record(702, "Cakes")],
        templates=[
            _template_record(320, "Product A", categ_id=702, sku="PA-1"),
            _template_record(321, "Product B", categ_id=702, sku="PB-1"),
        ],
        variants=[
            # Product A's variant claims "size" and "flavor" via two recognized-name
            # axes first, so its "Topping" axis (3rd) is forced past both positional
            # slots into a slugified code — deliberately NOT "size", so the next
            # test's assertion can't be satisfied by positional coincidence alone.
            _variant_record(420, 320, "Product A Variant", sku="PA-1-V", ptav_ids=[10, 11, 12]),
            # Product B's variant references the SAME Odoo attribute (id=99) as its
            # only axis — positional fallback alone would give it "size" (nothing else
            # claims a slot on this variant); only reuse-by-odoo-id gives the correct
            # "topping" (matching Product A).
            _variant_record(421, 321, "Product B Variant", sku="PB-1-V", ptav_ids=[13]),
        ],
        template_attribute_values=[
            _ptav_record(10, 201),
            _ptav_record(11, 202),
            _ptav_record(12, 203),
            _ptav_record(13, 204),
        ],
        attribute_values=[
            _attribute_value_record(201, "Small", attribute_id=1, attribute_name="Size"),
            _attribute_value_record(202, "Vanilla", attribute_id=5, attribute_name="Flavor"),
            _attribute_value_record(203, "Sprinkles", attribute_id=99, attribute_name="Topping"),
            _attribute_value_record(204, "Nuts", attribute_id=99, attribute_name="Topping"),
        ],
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-attr-2", full_resync=True
    )

    assert run.status == "SUCCEEDED"
    variant_a = (
        db_session.query(CatalogueProductVariant)
        .filter(CatalogueProductVariant.odoo_product_variant_id == 420)
        .one()
    )
    variant_b = (
        db_session.query(CatalogueProductVariant)
        .filter(CatalogueProductVariant.odoo_product_variant_id == 421)
        .one()
    )
    code_a = db_session.execute(
        text(
            "SELECT attribute_code FROM catalogue_product_attribute_values "
            "WHERE variant_id = :vid AND odoo_attribute_id = 99"
        ),
        {"vid": str(variant_a.id)},
    ).scalar_one()
    code_b = db_session.execute(
        text(
            "SELECT attribute_code FROM catalogue_product_attribute_values "
            "WHERE variant_id = :vid AND odoo_attribute_id = 99"
        ),
        {"vid": str(variant_b.id)},
    ).scalar_one()

    assert code_a not in ("size", "flavor")  # forced to a slugified code on Product A
    assert code_b == code_a  # Product B reuses it, not positional fallback's "size"


# -- stock (the real environment gap) -----------------------------------------------------


def test_sync_stock_degrades_gracefully_when_model_not_installed(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Protects the real, documented condition on the connected Odoo instance: the
    Inventory app isn't installed, so stock.quant reports "model not installed". This
    must degrade to PARTIALLY_COMPLETED, never FAILED — every other entity type still
    succeeds.
    """
    _fake_connected_client(
        monkeypatch,
        categories=[_category_record(803, "Cakes")],
        templates=[_template_record(224, "Carrot Cake", categ_id=803, sku="CC-1")],
        variants=[_variant_record(9002, 224, "Carrot Cake", sku="CC-1")],
        stock=OdooRemoteError("Object stock.quant doesn't exist", context={}),
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-7", full_resync=True
    )

    assert run.status == "PARTIALLY_COMPLETED"
    checkpoint_status = db_session.execute(
        text(
            "SELECT status FROM integration_sync_checkpoints WHERE integration_name = "
            "'odoo_catalogue' AND entity_type = 'PRODUCT_AVAILABILITY'"
        )
    ).scalar_one()
    assert checkpoint_status == "FAILED"
    # The other entity types still succeeded.
    product_count = _table_count(db_session, "catalogue_products")
    assert product_count == 1


# -- connectivity --------------------------------------------------------------------------


def test_sync_all_records_failed_run_when_odoo_unreachable(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        service_module, "_connect_readonly", lambda settings: (None, "connection refused")
    )
    service = OdooCatalogueSyncService(db_session)

    run = service.sync_all(trigger="MANUAL", initiated_by="test", correlation_id="corr-8")

    assert run.status == "FAILED"
    assert run.error_summary == "connection refused"
    # Scoped by correlation_id rather than a whole-table count: the admin-trigger
    # endpoint test runs the sync task via real Celery-eager dispatch (a separate,
    # actually-committed connection outside this test's own rollback), so other rows
    # can legitimately already exist in the shared test database.
    stored = db_session.execute(
        text("SELECT status FROM odoo_catalogue_sync_runs WHERE correlation_id = 'corr-8'")
    ).scalar_one()
    assert stored == "FAILED"


# -- incremental vs full resync -------------------------------------------------------------


def test_full_resync_ignores_checkpoint_domain(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _fake_connected_client(monkeypatch, categories=[_category_record(901, "Pastries")])
    service = OdooCatalogueSyncService(db_session)

    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-9", full_resync=True
    )

    category_call = next(
        c for c in transport.calls if c.args[3:5] == ["product.category", "search_read"]
    )
    assert category_call.args[5][0] == []  # empty domain = sweep everything


def test_incremental_sync_uses_checkpoint_watermark_on_second_run(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(monkeypatch, categories=[_category_record(902, "Pastries")])
    service = OdooCatalogueSyncService(db_session)
    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-10a", full_resync=True
    )

    transport = _fake_connected_client(monkeypatch, categories=[])
    service.sync_all(
        trigger="MANUAL", initiated_by="test", correlation_id="corr-10b", full_resync=False
    )

    category_call = next(
        c for c in transport.calls if c.args[3:5] == ["product.category", "search_read"]
    )
    domain = category_call.args[5][0]
    assert domain and domain[0][0] == "write_date" and domain[0][1] == ">="
