from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.integrations.odoo.client import OdooClient
from app.scripts import plan_odoo_catalogue_import as plan_script
from tests.unit.odoo.conftest import FakeTransport

CATEGORY = {
    "external_key": "terrific_bites.category.cupcakes",
    "code": "CUP",
    "code_requires_confirmation": True,
    "slug": "cupcakes",
    "name_en": "Cupcakes",
    "active": True,
    "display_order": 1,
}
PRODUCT = {
    "external_key": "terrific_bites.product.swiss-frosting",
    "sku": "TB-CUP-001",
    "sku_requires_confirmation": True,
    "slug": "swiss-frosting",
    "name_en": "Swiss Frosting",
    "category_external_key": "terrific_bites.category.cupcakes",
    "sales_price": 12.5,
    "currency": "SAR",
    "product_type": "simple",
    "active": True,
    "sellable": True,
}


def test_categories_blocked_when_no_odoo_connection() -> None:
    items = plan_script._plan_categories([CATEGORY], [], None, "Odoo unreachable", [], "corr-1")

    assert items[0].proposed_action == "BLOCKED"
    assert "Odoo unreachable" in items[0].blocking_issues[0]


def test_categories_create_when_no_match_and_no_open_decisions(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(("execute_kw", "product.category", "search_read"), [])

    items = plan_script._plan_categories([CATEGORY], [], authenticated_client, None, [], "corr-1")

    assert items[0].proposed_action == "CREATE"
    assert transport.write_call_count() == 0


def test_categories_blocked_when_business_decision_open(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(("execute_kw", "product.category", "search_read"), [])
    open_decision = {
        "decision_id": "D03",
        "title": "Category codes",
        "status": "BUSINESS_CONFIRMATION_REQUIRED",
    }

    items = plan_script._plan_categories(
        [CATEGORY], [open_decision], authenticated_client, None, [], "corr-1"
    )

    assert items[0].proposed_action == "BLOCKED"
    assert "D03" in items[0].blocking_issues[0]


def test_categories_match_by_external_key_when_xml_id_exists(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "ir.model.data", "search_read"),
        [
            {
                "id": 1,
                "res_id": 42,
                "module": "terrific_bites",
                "name": "category_cupcakes",
                "model": "product.category",
            }
        ],
    )

    items = plan_script._plan_categories([CATEGORY], [], authenticated_client, None, [], "corr-1")

    assert items[0].proposed_action == "MATCH_BY_EXTERNAL_KEY"
    assert items[0].existing_match is not None
    assert items[0].existing_match["res_id"] == 42


def test_categories_match_by_name_when_no_external_key_but_name_collides(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(
        ("execute_kw", "product.category", "search_read"), [{"id": 9, "name": "Cupcakes"}]
    )

    items = plan_script._plan_categories([CATEGORY], [], authenticated_client, None, [], "corr-1")

    assert items[0].proposed_action == "MATCH_BY_NAME_REVIEW_REQUIRED"
    assert items[0].warnings


def test_products_match_by_sku(authenticated_client: OdooClient, transport: FakeTransport) -> None:
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(
        ("execute_kw", "product.template", "search_read"), [{"id": 3, "default_code": "TB-CUP-001"}]
    )

    items = plan_script._plan_products([PRODUCT], [], authenticated_client, None, [], "corr-1")

    assert items[0].proposed_action == "MATCH_BY_SKU"
    assert transport.write_call_count() == 0


def test_products_blocked_when_no_odoo_connection() -> None:
    items = plan_script._plan_products([PRODUCT], [], None, "not configured", [], "corr-1")

    assert items[0].proposed_action == "BLOCKED"


def test_main_end_to_end_against_real_canonical_files_with_odoo_unconfigured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unconfigured = Settings(_env_file=None, odoo_base_url="", odoo_database="", odoo_username="")
    monkeypatch.setattr(plan_script, "get_settings", lambda: unconfigured)
    output_path = tmp_path / "plan.json"

    exit_code = plan_script.main(["--output", str(output_path)])

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["blocking_item_count"] > 0
    assert all(item["proposed_action"] == "BLOCKED" for item in report["categories"])
    assert all(item["proposed_action"] == "BLOCKED" for item in report["products"])
    assert len(report["categories"]) == 6
    assert len(report["products"]) == 26
