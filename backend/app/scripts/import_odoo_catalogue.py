"""Phase 5 controlled Odoo catalogue importer.

Usage:
    python -m app.scripts.import_odoo_catalogue --validate
    python -m app.scripts.import_odoo_catalogue --plan [--output PATH]
    python -m app.scripts.import_odoo_catalogue --dry-run [--output PATH]
    python -m app.scripts.import_odoo_catalogue --apply --confirm-import [--allow-partial]
    python -m app.scripts.import_odoo_catalogue --reconcile [--run-id UUID] [--output PATH]

Modes are mutually exclusive — exactly one of --validate/--plan/--dry-run/--apply/
--reconcile must be given.

--apply performs real Odoo writes and is refused unless ALL of the following hold:
    1. --confirm-import was explicitly passed (--apply alone does nothing).
    2. Every blocking decision in data/catalogue/catalogue-business-approvals.json is
       APPROVED with a non-null approved_value (see check_catalogue_import_approvals).
    3. The live Odoo company currency is SAR.
    4. Zero plan items are BLOCKED, unless --allow-partial was also passed — in which
       case only the unblocked items are imported and the run is recorded as
       PARTIALLY_COMPLETED.

Exit codes:
    0 — the requested mode completed as expected (for --apply/--dry-run: no FAILED
        items; for --validate/--plan: environment+catalogue+approvals all clean;
        for --reconcile: no mismatches found).
    1 — the mode ran but found something wrong (validation issues, blocked plan
        items, failed writes, reconciliation mismatches).
    2 — --apply was refused before any Odoo write was attempted (ImportBlockedError).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.core.database import session_scope
from app.services.catalogue.odoo_import_planning import ImportPlan
from app.services.catalogue.odoo_import_service import (
    ImportBlockedError,
    OdooCatalogueImportService,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLAN_OUTPUT = REPO_ROOT / "data" / "odoo" / "catalogue-import-execution-plan.json"
DEFAULT_DRY_RUN_OUTPUT = REPO_ROOT / "data" / "odoo" / "catalogue-import-dry-run-report.json"
DEFAULT_RECONCILE_OUTPUT = (
    REPO_ROOT / "data" / "odoo" / "catalogue-import-reconciliation-report.json"
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--reconcile", action="store_true")

    parser.add_argument(
        "--confirm-import",
        action="store_true",
        help="Required in addition to --apply — makes accidental writes harder.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="With --apply: import only unblocked items instead of refusing the whole run. "
        "Default false — do not use for the initial production import without explicit sign-off.",
    )
    parser.add_argument("--run-id", help="With --reconcile: a specific import_run_id (UUID).")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--initiated-by", default="cli")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _plan_to_dict(plan: ImportPlan) -> dict[str, Any]:
    return {
        "generated_at": plan.generated_at,
        "environment": asdict(plan.environment) if plan.environment else None,
        "environment_fingerprint": plan.environment.fingerprint if plan.environment else None,
        "connection_error": plan.connection_error,
        "source_checksum": plan.source_checksum,
        "approval_checksum": plan.approval_checksum,
        "import_plan_checksum": plan.compute_plan_checksum(),
        "action_counts": plan.action_counts,
        "blocking_item_count": len(plan.blocked_items),
        "categories": [asdict(i) for i in plan.category_items],
        "products": [asdict(i) for i in plan.product_items],
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def _run_validate(args: argparse.Namespace) -> int:
    with session_scope() as session:
        service = OdooCatalogueImportService(session)
        report = service.run_validate()
        session.rollback()  # validate never writes anything, even a run row

    payload = {"ok": report.ok, "checks": report.checks, "issues": report.issues}
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"Validation: {'OK' if report.ok else 'FAILED'}")
        for issue in report.issues:
            print(f"  - {issue}")
    return 0 if report.ok else 1


def _run_plan(args: argparse.Namespace) -> int:
    correlation_id = f"import_plan_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        service = OdooCatalogueImportService(session)
        plan = service.run_plan(initiated_by=args.initiated_by, correlation_id=correlation_id)
        session.commit()

    report = _plan_to_dict(plan)
    output = args.output or DEFAULT_PLAN_OUTPUT
    _write_report(output, report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(
            f"Odoo connection: {'ok' if plan.connection_error is None else plan.connection_error}"
        )
        print(f"Action counts:   {plan.action_counts}")
        print(f"Blocked items:   {len(plan.blocked_items)}")
        print(f"\nFull plan written to {output}")
    return 1 if plan.blocked_items else 0


def _run_dry_run(args: argparse.Namespace) -> int:
    correlation_id = f"import_dry_run_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        service = OdooCatalogueImportService(session)
        plan, run = service.run_dry_run(
            initiated_by=args.initiated_by, correlation_id=correlation_id
        )
        session.commit()
        run_id = str(run.id)

    report = _plan_to_dict(plan)
    report["import_run_id"] = run_id
    output = args.output or DEFAULT_DRY_RUN_OUTPUT
    _write_report(output, report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"Dry run recorded as import_run_id={run_id}")
        print(f"Action counts: {plan.action_counts}")
        print(f"Blocked items: {len(plan.blocked_items)}")
        print(f"\nFull report written to {output}")
    return 1 if plan.blocked_items else 0


def _run_apply(args: argparse.Namespace) -> int:
    correlation_id = f"import_apply_{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        service = OdooCatalogueImportService(session)
        try:
            result = service.run_apply(
                confirmed=args.confirm_import,
                allow_partial=args.allow_partial,
                initiated_by=args.initiated_by,
                correlation_id=correlation_id,
            )
        except ImportBlockedError as exc:
            session.rollback()
            print(f"APPLY BLOCKED: {exc}")
            return 2
        session.commit()

    print(f"Apply run {result.run.id}: {result.run.status}")
    print(
        f"  created={result.run.actual_create_count} "
        f"updated={result.run.actual_update_count} "
        f"skipped={result.run.actual_skip_count} "
        f"failed={result.run.actual_failed_count}"
    )
    return 0 if result.run.status == "SUCCEEDED" else 1


def _run_reconcile(args: argparse.Namespace) -> int:
    with session_scope() as session:
        service = OdooCatalogueImportService(session)
        report = service.run_reconcile(args.run_id)
        session.rollback()  # reconcile never writes anything

    output = args.output or DEFAULT_RECONCILE_OUTPUT
    _write_report(output, report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        if report.get("run_id") is None:
            status_label = "NOTHING TO RECONCILE"
        elif report.get("clean"):
            status_label = "CLEAN"
        else:
            status_label = "MISMATCHES FOUND"
        print(f"Reconciliation for run_id={report.get('run_id')}: {status_label}")
        for error in report.get("errors", []):
            print(f"  - {error}")
        print(f"Items checked: {report.get('items_checked')}")
        print(f"Field mismatches: {len(report.get('field_mismatches', []))}")
        print(
            f"PostgreSQL mapping mismatches: {len(report.get('postgresql_mapping_mismatches', []))}"
        )
        print(f"\nFull report written to {output}")
    return 0 if report.get("clean") else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.validate:
        return _run_validate(args)
    if args.plan:
        return _run_plan(args)
    if args.dry_run:
        return _run_dry_run(args)
    if args.apply:
        return _run_apply(args)
    if args.reconcile:
        return _run_reconcile(args)
    return 2  # unreachable — argparse's mutually-exclusive group enforces one is set


if __name__ == "__main__":
    sys.exit(main())
