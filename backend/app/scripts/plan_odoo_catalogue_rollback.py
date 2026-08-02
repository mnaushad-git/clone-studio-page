"""Rollback *planning* for a Phase 5 Odoo catalogue import run — never destructive.

Usage:
    python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id <uuid>
    python -m app.scripts.plan_odoo_catalogue_rollback --import-run-id <uuid> --json

Reads odoo_catalogue_import_runs/odoo_catalogue_import_items for the given run and
classifies every item into one rollback category. This script never calls Odoo and
never deletes/archives anything — it only reads PostgreSQL and prints/writes a plan a
human executes manually. See docs/integrations/odoo-import-rollback.md for the manual
recovery procedures each classification implies.

Classifications:
    SAFE_TO_ARCHIVE       — a category/product this run *created*. Recommend
                             archiving (active=False) rather than deleting; this
                             script does not do it automatically.
    SAFE_TO_RESTORE        — a category/product this run *updated* an existing
                             record's fields on. before_state_json has the pre-import
                             values a human can write back.
    MANUAL_REVIEW_REQUIRED — an image this run created (Odoo has no clean archive
                              semantics for product.image), or any item whose
                              classification is ambiguous.
    NOT_ROLLBACKABLE        — an external XML ID (ir.model.data) this run created.
                              Never deleted automatically; see the doc for the manual
                              ir.model.data cleanup procedure if a full rollback is
                              genuinely required.
    NO_ACTION_REQUIRED      — MATCH (nothing was created/changed), BLOCKED, SKIPPED,
                              or FAILED items — there is nothing in Odoo to roll back.

Exit codes:
    0 — plan produced successfully (regardless of what it recommends).
    2 — the given import_run_id does not exist.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from app.core.database import session_scope
from app.models.integration.odoo_import_item import OdooCatalogueImportItem
from app.repositories.integration import OdooImportItemRepository, OdooImportRunRepository

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "odoo" / "catalogue-import-rollback-plan.json"


def _classify_item(item: OdooCatalogueImportItem) -> tuple[str, str]:
    if item.result_status in ("FAILED", "BLOCKED", "SKIPPED"):
        return "NO_ACTION_REQUIRED", "No Odoo write happened for this item."

    if item.result_status != "SUCCEEDED":
        return "MANUAL_REVIEW_REQUIRED", f"Unexpected result_status={item.result_status!r}."

    if item.entity_type == "EXTERNAL_XML_ID":
        if item.actual_action == "CREATE":
            return (
                "NOT_ROLLBACKABLE",
                "ir.model.data row created by this run. Not deleted automatically — see "
                "docs/integrations/odoo-import-rollback.md for the manual ir.model.data "
                "cleanup procedure if a full rollback is genuinely required.",
            )
        return "NO_ACTION_REQUIRED", "No XML ID write happened."

    if item.entity_type == "PRODUCT_IMAGE":
        if item.actual_action == "CREATE":
            return (
                "MANUAL_REVIEW_REQUIRED",
                "Image created by this run (product.template.image_1920 write or "
                "product.image record). Odoo has no clean 'archive' semantics for images — "
                "review and remove manually if rollback is required.",
            )
        return "NO_ACTION_REQUIRED", "Image was matched/skipped, not created."

    # CATEGORY / PRODUCT_TEMPLATE / PRODUCT_VARIANT
    if item.actual_action == "CREATE":
        return (
            "SAFE_TO_ARCHIVE",
            f"{item.odoo_model} id={item.odoo_record_id} created by this run. Recommend "
            "setting active=False rather than deleting — this script does not do it "
            "automatically.",
        )
    if item.actual_action == "MATCH":
        if item.written_values_json:
            return (
                "SAFE_TO_RESTORE",
                f"{item.odoo_model} id={item.odoo_record_id} was an existing record this run "
                "updated. before_state_json has the pre-import values to write back.",
            )
        return "NO_ACTION_REQUIRED", "Matched an existing record; no fields were changed."

    return "MANUAL_REVIEW_REQUIRED", f"Unrecognized actual_action={item.actual_action!r}."


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--import-run-id", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        run_id = uuid.UUID(args.import_run_id)
    except ValueError:
        print(f"--import-run-id is not a valid UUID: {args.import_run_id!r}")
        return 2

    with session_scope() as session:
        runs = OdooImportRunRepository(session)
        items_repo = OdooImportItemRepository(session)

        run = runs.get_by_id(run_id)
        if run is None:
            print(f"No odoo_catalogue_import_runs row found for id={run_id}")
            return 2

        items = items_repo.list_for_run(run_id)
        run_mode = run.mode
        run_status = run.status

        classified: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        for item in items:
            classification, reason = _classify_item(item)
            counts[classification] = counts.get(classification, 0) + 1
            classified.append(
                {
                    "entity_type": item.entity_type,
                    "canonical_external_key": item.canonical_external_key,
                    "odoo_model": item.odoo_model,
                    "odoo_record_id": item.odoo_record_id,
                    "external_xml_id": item.external_xml_id,
                    "actual_action": item.actual_action,
                    "result_status": item.result_status,
                    "before_state_json": item.before_state_json,
                    "classification": classification,
                    "reason": reason,
                }
            )
        session.rollback()  # read-only — never persist anything from this script

    report = {
        "import_run_id": str(run_id),
        "run_mode": run_mode,
        "run_status": run_status,
        "classification_counts": counts,
        "items": classified,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Rollback plan for import_run_id={run_id} (mode={run_mode}, status={run_status})")
        for classification, count in sorted(counts.items()):
            print(f"  {classification}: {count}")
        print(f"\nFull plan written to {args.output}")
        print(
            "\nNo automatic archive/restore/delete was performed — this is a plan only. "
            "See docs/integrations/odoo-import-rollback.md for manual execution steps."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
