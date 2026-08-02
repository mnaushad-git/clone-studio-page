from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.catalogue.approval_gate import (
    ApprovalFileError,
    compute_approval_checksum,
    evaluate_approval_gate,
    load_business_approvals,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_APPROVALS_PATH = REPO_ROOT / "data" / "catalogue" / "catalogue-business-approvals.json"


def _decision(**overrides: Any) -> dict[str, Any]:
    base = {
        "decision_id": "D99",
        "title": "Test decision",
        "proposed_value": {"x": 1},
        "approved_value": None,
        "status": "PROPOSED",
        "approved_by": None,
        "approved_at": None,
        "approval_notes": None,
        "evidence": {},
        "blocks_import": True,
    }
    base.update(overrides)
    return base


def _write_approvals(path: Path, decisions: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps({"generated_at": "2026-07-28T00:00:00Z", "decisions": decisions}),
        encoding="utf-8",
    )


# -- real file (the one CLAUDE.md Phase 5 requires check_catalogue_import_approvals to read) --


def test_real_approval_file_parses_and_has_seven_decisions() -> None:
    decisions = load_business_approvals(REAL_APPROVALS_PATH)
    ids = {d.decision_id for d in decisions}
    assert ids == {"D03", "D04", "D08", "D09", "D10", "D19", "D20"}


def test_real_approval_file_d09_is_approved_and_non_blocking_for_import() -> None:
    decisions = load_business_approvals(REAL_APPROVALS_PATH)
    d09 = next(d for d in decisions if d.decision_id == "D09")
    assert d09.status == "APPROVED"
    assert d09.approved_value is not None
    assert d09.is_resolved_approval is True


def test_real_approval_file_gate_is_satisfied() -> None:
    """Phase 6 recorded explicit business sign-off for D03/D04/D08/D10/D19 (D09 was
    already APPROVED) — all six blocking decisions are now APPROVED with a non-null
    approved_value, so the gate is satisfied. If this test starts failing because it
    flips back to unsatisfied, a decision's approval was reverted — investigate,
    don't just flip this assertion back.
    """
    decisions = load_business_approvals(REAL_APPROVALS_PATH)
    result = evaluate_approval_gate(decisions)
    assert result.all_blocking_resolved is True
    assert result.unresolved == []
    assert result.rejected == []
    assert {d.decision_id for d in result.approved} == {"D03", "D04", "D08", "D10", "D19"}


def test_real_approval_file_d20_is_deliberately_unapproved_and_non_blocking() -> None:
    """D20 (Odoo native product-attribute/variant modeling activation) is new, higher-
    risk write surface — deliberately left PROPOSED (not yet approved) and
    blocks_import=false, so it gates only PRODUCT_ATTRIBUTE/PRODUCT_ATTRIBUTE_VALUE/
    PRODUCT_VARIANT plan items (via VARIANT_BLOCKING_DECISION_IDS in
    odoo_import_planning.py) without blocking the overall category/template --apply
    gate this test file otherwise asserts is satisfied.
    """
    decisions = load_business_approvals(REAL_APPROVALS_PATH)
    d20 = next(d for d in decisions if d.decision_id == "D20")
    assert d20.blocks_import is False
    assert d20.status != "APPROVED"
    assert d20.is_resolved_approval is True  # non-blocking decisions are trivially resolved


# -- schema validation ------------------------------------------------------------------


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ApprovalFileError, match="not found"):
        load_business_approvals(tmp_path / "does-not-exist.json")


def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ApprovalFileError, match="not valid JSON"):
        load_business_approvals(path)


def test_missing_required_field_raises(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    decision = _decision()
    del decision["blocks_import"]
    _write_approvals(path, [decision])
    with pytest.raises(ApprovalFileError, match="blocks_import"):
        load_business_approvals(path)


def test_invalid_status_value_raises(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="MAYBE")])
    with pytest.raises(ApprovalFileError, match="status"):
        load_business_approvals(path)


def test_duplicate_decision_id_raises(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(), _decision()])
    with pytest.raises(ApprovalFileError, match="Duplicate"):
        load_business_approvals(path)


def test_empty_decisions_list_raises(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [])
    with pytest.raises(ApprovalFileError, match="empty"):
        load_business_approvals(path)


# -- gate evaluation ---------------------------------------------------------------------


def test_unresolved_blocking_decision_blocks_gate(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="PROPOSED")])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is False
    assert len(result.unresolved) == 1


def test_rejected_blocking_decision_blocks_gate(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="REJECTED")])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is False
    assert len(result.rejected) == 1
    assert len(result.unresolved) == 0


def test_approved_with_value_satisfies_gate(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="APPROVED", approved_value={"x": 1})])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is True
    assert len(result.approved) == 1


def test_approved_status_but_null_value_does_not_satisfy_gate(tmp_path: Path) -> None:
    """A decision can't be marked APPROVED with approved_value still null — the gate
    must treat that as unresolved, not silently accept it (CLAUDE.md Phase 5 §1:
    "Import apply mode must reject any decision where ... approved_value is null").
    """
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="APPROVED", approved_value=None)])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is False
    assert len(result.unresolved) == 1


def test_non_blocking_decision_never_blocks_gate_regardless_of_status(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="PROPOSED", blocks_import=False)])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is True
    assert len(result.non_blocking) == 1


def test_requires_clarification_is_treated_as_unresolved(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="REQUIRES_CLARIFICATION")])
    decisions = load_business_approvals(path)

    result = evaluate_approval_gate(decisions)

    assert result.all_blocking_resolved is False
    assert len(result.unresolved) == 1


# -- checksum -----------------------------------------------------------------------------


def test_checksum_is_stable_for_same_input(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="APPROVED", approved_value={"x": 1})])
    decisions = load_business_approvals(path)

    assert compute_approval_checksum(decisions) == compute_approval_checksum(decisions)


def test_checksum_changes_when_a_decision_changes(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(path, [_decision(status="PROPOSED")])
    before = load_business_approvals(path)

    _write_approvals(path, [_decision(status="APPROVED", approved_value={"x": 1})])
    after = load_business_approvals(path)

    assert compute_approval_checksum(before) != compute_approval_checksum(after)


def test_checksum_is_order_independent(tmp_path: Path) -> None:
    path = tmp_path / "approvals.json"
    _write_approvals(
        path,
        [
            _decision(decision_id="D01", status="APPROVED", approved_value=1),
            _decision(decision_id="D02", status="APPROVED", approved_value=2),
        ],
    )
    forward = load_business_approvals(path)

    _write_approvals(
        path,
        [
            _decision(decision_id="D02", status="APPROVED", approved_value=2),
            _decision(decision_id="D01", status="APPROVED", approved_value=1),
        ],
    )
    reversed_ = load_business_approvals(path)

    assert compute_approval_checksum(forward) == compute_approval_checksum(reversed_)
