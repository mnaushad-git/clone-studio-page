"""Read-only dry-run catalogue import planner.

Usage:
    python -m app.scripts.plan_odoo_catalogue_import
    python -m app.scripts.plan_odoo_catalogue_import --json \
        --output data/odoo/catalogue-import-plan.json

Reads the canonical catalogue files (data/catalogue/categories.json,
data/catalogue/products.json) and data/catalogue/catalogue-decisions.json, attempts a
fresh read-only Odoo connection to search for existing matches/conflicts, and
produces one planned action per category/product. Never creates, updates, archives,
or deletes anything in Odoo — every Odoo call here goes through
app.integrations.odoo.client.OdooClient's read-only surface, same as
verify_odoo_connection.

Exit codes:
    0 — every item resolved to a safe action with no blocking issues.
    1 — at least one item is BLOCKED (Odoo unreachable, an open business/Odoo-config
        decision, or a genuine name/SKU conflict).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.discovery.catalogue_mapping import (
    MappingClassification,
    build_category_mapping,
    build_product_mapping,
)
from app.integrations.odoo.discovery.fields import (
    CATALOGUE_RELEVANT_MODELS,
    discover_fields_for_models,
)
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooIntegrationError
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.products import OdooProductRepository
from app.integrations.odoo.transport import OdooTransport

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data" / "catalogue"
DEFAULT_PLAN_PATH = REPO_ROOT / "data" / "odoo" / "catalogue-import-plan.json"

CATEGORY_BLOCKING_DECISION_IDS = {"D03"}
PRODUCT_BLOCKING_DECISION_IDS = {"D04", "D08", "D09", "D10", "D19"}


@dataclass
class PlannedItem:
    entity_type: str
    external_key: str
    identifier: str
    canonical_name: str
    proposed_odoo_model: str
    existing_match: dict[str, Any] | None
    match_strategy: str | None
    proposed_action: str
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mapped_fields: dict[str, Any] = field(default_factory=dict)
    omitted_postgresql_only_fields: list[str] = field(default_factory=list)
    confirmation_status: dict[str, Any] = field(default_factory=dict)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_PLAN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _open_decisions(decisions: list[dict[str, Any]], ids: set[str]) -> list[dict[str, Any]]:
    return [
        d
        for d in decisions
        if d["decision_id"] in ids and d.get("blocks_odoo_import") and d.get("status") != "APPROVED"
    ]


def _connect() -> tuple[OdooClient | None, OdooTransport | None, str | None]:
    settings = get_settings()
    if not OdooConfig.is_configured(settings):
        return None, None, "Odoo is not configured (ODOO_BASE_URL/DATABASE/USERNAME empty)"
    try:
        config = OdooConfig.from_settings(settings)
    except OdooConfigurationError as exc:
        return None, None, f"Invalid Odoo configuration: {exc}"

    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    try:
        client.get_server_version()
        client.authenticate()
    except OdooIntegrationError as exc:
        transport.close()
        return None, None, f"Could not establish a verified Odoo session: {exc}"
    return client, transport, None


def _external_key_match(
    client: OdooClient, model: str, xml_id_name: str, correlation_id: str
) -> dict[str, Any] | None:
    """Looks for an existing ir.model.data row under the terrific_bites module
    namespace — the D20 external-key strategy. No xml_id is ever created in this
    phase, so a match here only happens if a prior (out-of-band) import already ran.
    """
    try:
        page = client.search_read(
            "ir.model.data",
            [["module", "=", "terrific_bites"], ["name", "=", xml_id_name], ["model", "=", model]],
            ["id", "res_id", "module", "name", "model"],
            limit=1,
            correlation_id=correlation_id,
        )
    except OdooIntegrationError:
        return None
    return page.records[0] if page.records else None


def _omitted_fields(mapping: list[Any]) -> list[str]:
    return [
        m.canonical_field
        for m in mapping
        if m.classification == MappingClassification.POSTGRESQL_ONLY
    ]


def _plan_categories(
    categories: list[dict[str, Any]],
    open_decisions: list[dict[str, Any]],
    client: OdooClient | None,
    connect_failure: str | None,
    category_mapping: list[Any],
    correlation_id: str,
) -> list[PlannedItem]:
    repo = OdooCategoryRepository(client) if client else None
    omitted = _omitted_fields(category_mapping)
    items: list[PlannedItem] = []

    for category in categories:
        xml_id_name = f"category_{category['slug']}"
        mapped_fields = {
            "name_en": category["name_en"],
            "code": category["code"],
            "slug": category["slug"],
            "active": category.get("active", True),
            "display_order": category.get("display_order"),
        }
        confirmation_status = {
            "code": "BUSINESS_CONFIRMATION_REQUIRED"
            if category.get("code_requires_confirmation")
            else "APPROVED",
        }

        if client is None or repo is None:
            items.append(
                PlannedItem(
                    "category",
                    category["external_key"],
                    category["code"],
                    category["name_en"],
                    "product.category",
                    None,
                    None,
                    "BLOCKED",
                    blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        external_match = _external_key_match(
            client, "product.category", xml_id_name, correlation_id
        )
        if external_match:
            items.append(
                PlannedItem(
                    "category",
                    category["external_key"],
                    category["code"],
                    category["name_en"],
                    "product.category",
                    external_match,
                    "EXTERNAL_KEY",
                    "MATCH_BY_EXTERNAL_KEY",
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        name_matches = repo.find_by_name(category["name_en"], correlation_id=correlation_id)
        if name_matches:
            items.append(
                PlannedItem(
                    "category",
                    category["external_key"],
                    category["code"],
                    category["name_en"],
                    "product.category",
                    name_matches[0],
                    "NAME",
                    "MATCH_BY_NAME_REVIEW_REQUIRED",
                    warnings=[
                        f"An existing product.category named {category['name_en']!r} was found "
                        "(id={}) — confirm this is/isn't the same category before import.".format(
                            name_matches[0]["id"]
                        )
                    ],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        relevant_open = [
            d for d in open_decisions if d["decision_id"] in CATEGORY_BLOCKING_DECISION_IDS
        ]
        if relevant_open:
            items.append(
                PlannedItem(
                    "category",
                    category["external_key"],
                    category["code"],
                    category["name_en"],
                    "product.category",
                    None,
                    None,
                    "BLOCKED",
                    blocking_issues=[
                        f"{d['decision_id']} ({d['title']}) is {d['status']}, not APPROVED"
                        for d in relevant_open
                    ],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        items.append(
            PlannedItem(
                "category",
                category["external_key"],
                category["code"],
                category["name_en"],
                "product.category",
                None,
                None,
                "CREATE",
                mapped_fields=mapped_fields,
                omitted_postgresql_only_fields=omitted,
                confirmation_status=confirmation_status,
            )
        )

    return items


def _plan_products(
    products: list[dict[str, Any]],
    open_decisions: list[dict[str, Any]],
    client: OdooClient | None,
    connect_failure: str | None,
    product_mapping: list[Any],
    correlation_id: str,
) -> list[PlannedItem]:
    repo = OdooProductRepository(client) if client else None
    omitted = _omitted_fields(product_mapping)
    items: list[PlannedItem] = []

    for product in products:
        xml_id_name = f"product_{product['slug']}"
        mapped_fields = {
            "name_en": product["name_en"],
            "sku": product["sku"],
            "slug": product["slug"],
            "category_external_key": product["category_external_key"],
            "sales_price": product["sales_price"],
            "currency": product["currency"],
            "product_type": product.get("product_type"),
            "active": product.get("active", True),
            "sellable": product.get("sellable", True),
        }
        confirmation_status = {
            "sku": "BUSINESS_CONFIRMATION_REQUIRED"
            if product.get("sku_requires_confirmation")
            else "APPROVED",
        }

        if client is None or repo is None:
            items.append(
                PlannedItem(
                    "product",
                    product["external_key"],
                    product["sku"],
                    product["name_en"],
                    "product.template",
                    None,
                    None,
                    "BLOCKED",
                    blocking_issues=[f"Cannot verify against Odoo: {connect_failure}"],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        external_match = _external_key_match(
            client, "product.template", xml_id_name, correlation_id
        )
        if external_match:
            items.append(
                PlannedItem(
                    "product",
                    product["external_key"],
                    product["sku"],
                    product["name_en"],
                    "product.template",
                    external_match,
                    "EXTERNAL_KEY",
                    "MATCH_BY_EXTERNAL_KEY",
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        sku_matches = repo.find_templates_by_default_code(
            product["sku"], correlation_id=correlation_id
        )
        if sku_matches:
            items.append(
                PlannedItem(
                    "product",
                    product["external_key"],
                    product["sku"],
                    product["name_en"],
                    "product.template",
                    sku_matches[0],
                    "SKU",
                    "MATCH_BY_SKU",
                    warnings=[
                        f"An existing product.template with default_code={product['sku']!r} was "
                        f"found (id={sku_matches[0]['id']}) — confirm it is/isn't the same product."
                    ],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        name_matches = repo.find_templates_by_name(
            product["name_en"], correlation_id=correlation_id
        )
        if name_matches:
            items.append(
                PlannedItem(
                    "product",
                    product["external_key"],
                    product["sku"],
                    product["name_en"],
                    "product.template",
                    name_matches[0],
                    "NAME",
                    "MATCH_BY_NAME_REVIEW_REQUIRED",
                    warnings=[
                        f"An existing product.template named {product['name_en']!r} was found "
                        f"(id={name_matches[0]['id']}) with a different/absent SKU — review "
                        "before import."
                    ],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        relevant_open = [
            d for d in open_decisions if d["decision_id"] in PRODUCT_BLOCKING_DECISION_IDS
        ]
        if relevant_open:
            items.append(
                PlannedItem(
                    "product",
                    product["external_key"],
                    product["sku"],
                    product["name_en"],
                    "product.template",
                    None,
                    None,
                    "BLOCKED",
                    blocking_issues=[
                        f"{d['decision_id']} ({d['title']}) is {d['status']}, not APPROVED"
                        for d in relevant_open
                    ],
                    mapped_fields=mapped_fields,
                    omitted_postgresql_only_fields=omitted,
                    confirmation_status=confirmation_status,
                )
            )
            continue

        items.append(
            PlannedItem(
                "product",
                product["external_key"],
                product["sku"],
                product["name_en"],
                "product.template",
                None,
                None,
                "CREATE",
                mapped_fields=mapped_fields,
                omitted_postgresql_only_fields=omitted,
                confirmation_status=confirmation_status,
            )
        )

    return items


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    correlation_id = f"plan_odoo_import_{uuid.uuid4().hex[:12]}"

    categories = _load_json(DATA_DIR / "categories.json")["categories"]
    products = _load_json(DATA_DIR / "products.json")["products"]
    decisions = _load_json(DATA_DIR / "catalogue-decisions.json")["decisions"]

    category_open = _open_decisions(decisions, CATEGORY_BLOCKING_DECISION_IDS)
    product_open = _open_decisions(decisions, PRODUCT_BLOCKING_DECISION_IDS)

    client, transport, connect_failure = _connect()
    try:
        fields_by_model = (
            discover_fields_for_models(
                client, CATALOGUE_RELEVANT_MODELS, correlation_id=correlation_id
            )
            if client
            else None
        )
        category_mapping = build_category_mapping(fields_by_model)
        product_mapping = build_product_mapping(fields_by_model)

        category_items = _plan_categories(
            categories, category_open, client, connect_failure, category_mapping, correlation_id
        )
        product_items = _plan_products(
            products, product_open, client, connect_failure, product_mapping, correlation_id
        )
    finally:
        if transport:
            transport.close()

    all_items = category_items + product_items
    blocking_items = [i for i in all_items if i.proposed_action == "BLOCKED"]
    action_counts: dict[str, int] = {}
    for item in all_items:
        action_counts[item.proposed_action] = action_counts.get(item.proposed_action, 0) + 1

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "odoo_connection": "ok" if client else f"unavailable: {connect_failure}",
        "unresolved_required_configuration": [
            {"decision_id": d["decision_id"], "title": d["title"], "status": d["status"]}
            for d in category_open + product_open
        ],
        "action_counts": action_counts,
        "blocking_item_count": len(blocking_items),
        "field_mappings": {
            "category": [m.to_dict() for m in category_mapping],
            "product": [m.to_dict() for m in product_mapping],
        },
        "categories": [asdict(i) for i in category_items],
        "products": [asdict(i) for i in product_items],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Odoo connection: {report['odoo_connection']}")
        print(f"Action counts:   {action_counts}")
        print(
            f"Unresolved required configuration: {len(report['unresolved_required_configuration'])}"
        )
        for d in report["unresolved_required_configuration"]:
            print(f"  - {d['decision_id']}: {d['title']} ({d['status']})")
        print(f"Blocking items:  {len(blocking_items)}")
        print(f"\nFull plan written to {args.output}")

    return 1 if blocking_items else 0


if __name__ == "__main__":
    sys.exit(main())
