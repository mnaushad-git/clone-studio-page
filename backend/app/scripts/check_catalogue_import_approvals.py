"""Report the Phase 5 business approval gate status.

Usage:
    python -m app.scripts.check_catalogue_import_approvals
    python -m app.scripts.check_catalogue_import_approvals --json
    python -m app.scripts.check_catalogue_import_approvals --file path/to/approvals.json

Reads data/catalogue/catalogue-business-approvals.json (never writes it), validates its
schema, and reports which blocking decisions are APPROVED, unresolved, or REJECTED.
Never prints approved_by/evidence values verbatim if they happen to look like secrets —
the approval file schema has no field intended to hold credentials, but this script
still never echoes raw file bytes, only the typed fields it parses.

Exit codes:
    0 — every blocks_import decision is APPROVED with a non-null approved_value.
    1 — at least one blocking decision is unresolved or REJECTED.
    2 — the approval file is missing or fails schema validation (can't be evaluated).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.services.catalogue.approval_gate import (
    DEFAULT_APPROVALS_PATH,
    ApprovalFileError,
    evaluate_approval_gate,
    load_business_approvals,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_APPROVALS_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        decisions = load_business_approvals(args.file)
    except ApprovalFileError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"Approval file could not be evaluated: {exc}")
        return 2

    result = evaluate_approval_gate(decisions)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
        return 0 if result.all_blocking_resolved else 1

    print(f"Approval file: {args.file}")
    print(f"Blocking decisions approved: {len(result.approved)}")
    for d in result.approved:
        print(f"  [APPROVED] {d.decision_id}: {d.title}")

    print(f"Unresolved decisions: {len(result.unresolved)}")
    for d in result.unresolved:
        print(f"  [{d.status}] {d.decision_id}: {d.title}")

    print(f"Rejected decisions: {len(result.rejected)}")
    for d in result.rejected:
        print(f"  [REJECTED] {d.decision_id}: {d.title}")

    if result.non_blocking:
        print(f"Non-blocking decisions (informational): {len(result.non_blocking)}")
        for d in result.non_blocking:
            print(f"  [{d.status}] {d.decision_id}: {d.title}")

    if result.all_blocking_resolved:
        print("\nAll blocking decisions are APPROVED — the approval gate is satisfied.")
    else:
        print(
            "\nApproval gate is NOT satisfied — "
            "import_odoo_catalogue --apply will be refused until every blocking "
            "decision above is APPROVED with a non-null approved_value."
        )

    return 0 if result.all_blocking_resolved else 1


if __name__ == "__main__":
    sys.exit(main())
