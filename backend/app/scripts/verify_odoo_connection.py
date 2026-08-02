"""Read-only Odoo environment verification CLI.

Usage:
    python -m app.scripts.verify_odoo_connection
    python -m app.scripts.verify_odoo_connection --check-connection
    python -m app.scripts.verify_odoo_connection --discover-capabilities --discover-fields
    python -m app.scripts.verify_odoo_connection --check-catalogue-conflicts --json
    python -m app.scripts.verify_odoo_connection --output data/odoo/odoo-environment-report.json

With no flags, runs every check. Every call this makes is read-only (see
app/integrations/odoo/client.py's READONLY_ALLOWED_METHODS) — this script never
creates, updates, archives, or deletes an Odoo record.

Exit codes:
    0 — fully verified, no blockers.
    1 — ran, but hit at least one blocker (unreachable model/field/access, etc.).
    2 — could not run at all (Odoo not configured, or configuration invalid).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.discovery.capabilities import (
    EnvironmentReport,
    run_environment_verification,
)
from app.integrations.odoo.discovery.catalogue_mapping import (
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
DEFAULT_REPORT_PATH = REPO_ROOT / "data" / "odoo" / "odoo-environment-report.json"
CATEGORIES_PATH = REPO_ROOT / "data" / "catalogue" / "categories.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "catalogue" / "products.json"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check-connection", action="store_true")
    parser.add_argument("--check-authentication", action="store_true")
    parser.add_argument("--discover-capabilities", action="store_true")
    parser.add_argument("--discover-fields", action="store_true")
    parser.add_argument("--check-catalogue-conflicts", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report to stdout")
    return parser.parse_args(argv)


def _requested_full_run(args: argparse.Namespace) -> bool:
    return not (
        args.check_connection
        or args.check_authentication
        or args.discover_capabilities
        or args.discover_fields
        or args.check_catalogue_conflicts
    )


def _load_catalogue_conflicts(client: OdooClient, correlation_id: str) -> dict[str, Any]:
    category_repo = OdooCategoryRepository(client)
    product_repo = OdooProductRepository(client)

    category_conflicts: list[dict[str, Any]] = []
    if CATEGORIES_PATH.exists():
        categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))["categories"]
        for category in categories:
            matches = category_repo.find_by_name(category["name_en"], correlation_id=correlation_id)
            if matches:
                category_conflicts.append(
                    {
                        "slug": category["slug"],
                        "name_en": category["name_en"],
                        "odoo_matches": matches,
                    }
                )

    product_conflicts: list[dict[str, Any]] = []
    if PRODUCTS_PATH.exists():
        products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))["products"]
        for product in products:
            sku_matches = product_repo.find_templates_by_default_code(
                product["sku"], correlation_id=correlation_id
            )
            name_matches = product_repo.find_templates_by_name(
                product["name_en"], correlation_id=correlation_id
            )
            if sku_matches or name_matches:
                product_conflicts.append(
                    {
                        "slug": product["slug"],
                        "sku": product["sku"],
                        "name_en": product["name_en"],
                        "odoo_matches_by_sku": sku_matches,
                        "odoo_matches_by_name": name_matches,
                    }
                )

    return {"categories": category_conflicts, "products": product_conflicts}


def _blocked_report(reason: str, base_url: str, database: str) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "protocol": "jsonrpc",
        "base_url": base_url,
        "database": database,
        "overall_status": "BLOCKED",
        "server_version": None,
        "authenticated": False,
        "authenticated_uid": None,
        "checks": [],
        "blocking_check_ids": ["configuration"],
        "blocker_reason": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    full_run = _requested_full_run(args)
    settings = get_settings()

    if not OdooConfig.is_configured(settings):
        report = _blocked_report(
            "Odoo is not configured: ODOO_BASE_URL/ODOO_DATABASE/ODOO_USERNAME are all empty. "
            "Set them in backend/.env (never commit real values) and re-run this command. "
            "See docs/integrations/odoo-environment-verification.md.",
            settings.odoo_base_url,
            settings.odoo_database,
        )
        _emit(report, args)
        return 2

    try:
        config = OdooConfig.from_settings(settings)
    except OdooConfigurationError as exc:
        report = _blocked_report(str(exc), settings.odoo_base_url, settings.odoo_database)
        _emit(report, args)
        return 2

    correlation_id = f"verify_odoo_{uuid.uuid4().hex[:12]}"
    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    output: dict[str, Any] = {
        "protocol": config.protocol,
        "base_url": config.base_url,
        "database": config.database,
    }

    try:
        env_report: EnvironmentReport | None = None
        if (
            full_run
            or args.check_connection
            or args.check_authentication
            or args.discover_capabilities
        ):
            env_report = run_environment_verification(config, client, correlation_id=correlation_id)
            output["environment"] = env_report.to_dict()

        if (full_run or args.discover_fields) and client.is_authenticated():
            fields_by_model = discover_fields_for_models(
                client, CATALOGUE_RELEVANT_MODELS, correlation_id=correlation_id
            )
            output["field_discovery"] = {
                model: (
                    {name: descriptor.field_type for name, descriptor in fields.items()}
                    if fields is not None
                    else None
                )
                for model, fields in fields_by_model.items()
            }
            output["catalogue_mapping"] = {
                "category": [m.to_dict() for m in build_category_mapping(fields_by_model)],
                "product": [m.to_dict() for m in build_product_mapping(fields_by_model)],
            }
        elif full_run or args.discover_fields:
            output["field_discovery"] = None
            output["catalogue_mapping"] = {
                "category": [m.to_dict() for m in build_category_mapping(None)],
                "product": [m.to_dict() for m in build_product_mapping(None)],
            }

        if (full_run or args.check_catalogue_conflicts) and client.is_authenticated():
            output["catalogue_conflicts"] = _load_catalogue_conflicts(client, correlation_id)
        elif full_run or args.check_catalogue_conflicts:
            output["catalogue_conflicts"] = None
    finally:
        transport.close()

    _emit(output, args)

    env = output.get("environment")
    if env is None:
        return 2
    if env["overall_status"] == "VERIFIED":
        return 0
    return 1


def _emit(report: dict[str, Any], args: argparse.Namespace) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return

    _print_summary(report)
    print(f"\nFull report written to {args.output}")


def _print_summary(report: dict[str, Any]) -> None:
    env = report.get("environment")
    print(f"Odoo protocol:  {report.get('protocol')}")
    print(f"Base URL:       {report.get('base_url') or '(not set)'}")
    print(f"Database:       {report.get('database') or '(not set)'}")

    if env is None:
        print(f"Status:         BLOCKED — {report.get('blocker_reason')}")
        return

    print(f"Overall status: {env['overall_status']}")
    if env.get("server_version"):
        print(f"Server version: {env['server_version']['server_version']}")
    print(f"Authenticated:  {env['authenticated']}")

    blockers = [c for c in env["checks"] if c["status"] == "BLOCKED"]
    if blockers:
        print(f"\nBlockers ({len(blockers)}):")
        for check in blockers:
            print(f"  - [{check['check_id']}] {check['description']}: {check['detail']}")
    else:
        print("\nNo blockers.")

    conflicts = report.get("catalogue_conflicts")
    if conflicts:
        cat_conf = len(conflicts.get("categories") or [])
        prod_conf = len(conflicts.get("products") or [])
        if cat_conf or prod_conf:
            print(
                f"\nCatalogue conflicts: {cat_conf} category name match(es), "
                f"{prod_conf} product SKU/name match(es)."
            )
        else:
            print("\nCatalogue conflicts: none found.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OdooIntegrationError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
