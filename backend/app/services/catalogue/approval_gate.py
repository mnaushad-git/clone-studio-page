"""Business approval gate for the Odoo catalogue importer (Phase 5).

Reads data/catalogue/catalogue-business-approvals.json and answers exactly one
question: is every decision that blocks_import actually APPROVED with a non-null
approved_value? Nothing in this module ever writes to the approval file — approving a
decision is a human editing that JSON file directly (or a future admin workflow), never
something a script does automatically (explicit instruction: "Do not auto-approve any
decision").

app.scripts.check_catalogue_import_approvals reports this gate's result on the command
line; app.services.catalogue.odoo_import_service calls the same evaluate_approval_gate()
function in-process before allowing --apply to proceed, so the two can never disagree.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STATUS_VALUES = frozenset({"PROPOSED", "APPROVED", "REJECTED", "REQUIRES_CLARIFICATION"})

REQUIRED_FIELDS = (
    "decision_id",
    "title",
    "proposed_value",
    "approved_value",
    "status",
    "approved_by",
    "approved_at",
    "approval_notes",
    "evidence",
    "blocks_import",
)

BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_APPROVALS_PATH = REPO_ROOT / "data" / "catalogue" / "catalogue-business-approvals.json"


class ApprovalFileError(Exception):
    """The approval file is missing, unreadable, or fails schema validation."""


@dataclass(frozen=True)
class ApprovalDecision:
    decision_id: str
    title: str
    status: str
    approved_value: Any
    blocks_import: bool
    approved_by: str | None
    approved_at: str | None
    approval_notes: str | None

    @property
    def is_resolved_approval(self) -> bool:
        """True only if this decision cannot block anything further: either it doesn't
        block import at all, or it does and is cleanly APPROVED with a real value.
        """
        if not self.blocks_import:
            return True
        return self.status == "APPROVED" and self.approved_value is not None


@dataclass(frozen=True)
class ApprovalGateResult:
    approved: list[ApprovalDecision]
    unresolved: list[ApprovalDecision]
    rejected: list[ApprovalDecision]
    non_blocking: list[ApprovalDecision]

    @property
    def all_blocking_resolved(self) -> bool:
        return not self.unresolved and not self.rejected

    def to_dict(self) -> dict[str, Any]:
        def _row(d: ApprovalDecision) -> dict[str, Any]:
            return {
                "decision_id": d.decision_id,
                "title": d.title,
                "status": d.status,
                "blocks_import": d.blocks_import,
                "approved_value": d.approved_value,
            }

        return {
            "all_blocking_resolved": self.all_blocking_resolved,
            "approved": [_row(d) for d in self.approved],
            "unresolved": [_row(d) for d in self.unresolved],
            "rejected": [_row(d) for d in self.rejected],
            "non_blocking": [_row(d) for d in self.non_blocking],
        }


def _validate_schema(raw: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if "decisions" not in raw or not isinstance(raw["decisions"], list):
        return ["Top-level 'decisions' key is missing or is not a list"]
    if not raw["decisions"]:
        issues.append("'decisions' list is empty")

    seen_ids: set[str] = set()
    for idx, entry in enumerate(raw["decisions"]):
        if not isinstance(entry, dict):
            issues.append(f"decisions[{idx}] is not an object")
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            issues.append(f"decisions[{idx}] missing required field(s): {', '.join(missing)}")
            continue
        if entry["status"] not in ALLOWED_STATUS_VALUES:
            issues.append(
                f"decisions[{idx}] ({entry['decision_id']}): status "
                f"{entry['status']!r} is not one of {sorted(ALLOWED_STATUS_VALUES)}"
            )
        if not isinstance(entry["blocks_import"], bool):
            issues.append(
                f"decisions[{idx}] ({entry['decision_id']}): blocks_import must be a boolean"
            )
        if entry["decision_id"] in seen_ids:
            issues.append(f"Duplicate decision_id: {entry['decision_id']!r}")
        seen_ids.add(entry["decision_id"])

    return issues


def load_business_approvals(path: Path = DEFAULT_APPROVALS_PATH) -> list[ApprovalDecision]:
    if not path.exists():
        raise ApprovalFileError(f"Approval file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApprovalFileError(f"Approval file is not valid JSON: {exc}") from exc

    issues = _validate_schema(raw)
    if issues:
        raise ApprovalFileError("Approval file failed schema validation: " + "; ".join(issues))

    return [
        ApprovalDecision(
            decision_id=entry["decision_id"],
            title=entry["title"],
            status=entry["status"],
            approved_value=entry["approved_value"],
            blocks_import=entry["blocks_import"],
            approved_by=entry.get("approved_by"),
            approved_at=entry.get("approved_at"),
            approval_notes=entry.get("approval_notes"),
        )
        for entry in raw["decisions"]
    ]


def evaluate_approval_gate(decisions: list[ApprovalDecision]) -> ApprovalGateResult:
    approved: list[ApprovalDecision] = []
    unresolved: list[ApprovalDecision] = []
    rejected: list[ApprovalDecision] = []
    non_blocking: list[ApprovalDecision] = []

    for decision in decisions:
        if not decision.blocks_import:
            non_blocking.append(decision)
            continue
        if decision.status == "REJECTED":
            rejected.append(decision)
        elif decision.is_resolved_approval:
            approved.append(decision)
        else:
            unresolved.append(decision)

    return ApprovalGateResult(
        approved=approved, unresolved=unresolved, rejected=rejected, non_blocking=non_blocking
    )


def compute_approval_checksum(decisions: list[ApprovalDecision]) -> str:
    """A stable checksum of every blocking decision's (decision_id, status,
    approved_value) — used by --apply to detect that the approval file changed between
    plan generation and apply execution (rejects a stale plan checksum).
    """
    import hashlib

    payload = json.dumps(
        [
            {"decision_id": d.decision_id, "status": d.status, "approved_value": d.approved_value}
            for d in sorted(decisions, key=lambda d: d.decision_id)
        ],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
