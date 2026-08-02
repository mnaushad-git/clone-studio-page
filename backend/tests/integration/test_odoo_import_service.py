"""Integration tests for the Phase 5 Odoo catalogue import service, run against real
PostgreSQL (see tests/conftest.py's db_session fixture — never SQLite, the same
constraint as the Phase 3 catalogue tests) and the actual canonical
data/catalogue/{categories,products}.json + data/catalogue/catalogue-business-
approvals.json files committed to this repo.

Odoo itself is never real here — _connect() is monkeypatched per test, exactly like
plan_odoo_catalogue_import's own script tests, so these tests never require a live
Odoo instance and never perform a real network call.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.odoo.client import OdooClient
from app.services.catalogue import odoo_import_service as service_module
from app.services.catalogue.approval_gate import ApprovalDecision
from app.services.catalogue.odoo_import_service import (
    ImportBlockedError,
    OdooCatalogueImportService,
)
from tests.unit.odoo.conftest import FakeTransport, make_config


def _table_count(session: Session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608


def _approval(
    decision_id: str, *, status: str = "PROPOSED", approved_value: Any = None, blocks: bool = True
) -> ApprovalDecision:
    return ApprovalDecision(
        decision_id=decision_id,
        title=f"Decision {decision_id}",
        status=status,
        approved_value=approved_value,
        blocks_import=blocks,
        approved_by=None,
        approved_at=None,
        approval_notes=None,
    )


def _fake_connected_client(monkeypatch: pytest.MonkeyPatch) -> FakeTransport:
    """Wires app.services.catalogue.odoo_import_service._connect() to return a fully
    authenticated OdooClient over a FakeTransport pre-loaded with "nothing exists
    yet" responses for every model plan_categories/plan_products/capture_environment_
    snapshot query — the real canonical catalogue then plans every category/product
    as either CREATE (if approvals allow) or BLOCKED (if not), never MATCH, since
    nothing is ever queued to "be found".
    """
    config = make_config()
    transport = FakeTransport()
    transport.queue(("common", "version"), {"server_version": "19.0-test"})
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "res.company", "search_read"),
        [{"id": 1, "name": "My Company", "currency_id": [151, "SAR"]}],
    )
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(("execute_kw", "product.category", "search_read"), [])
    transport.queue(("execute_kw", "product.template", "search_read"), [])
    transport.queue(("execute_kw", "product.attribute", "search_read"), [])
    transport.queue(("execute_kw", "product.attribute.value", "search_read"), [])
    transport.queue(("execute_kw", "product.product", "search_read"), [])

    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()

    monkeypatch.setattr(service_module, "_connect", lambda: (client, None))
    return transport


# -- --apply refusal gates (no Odoo/DB writes should happen for any of these) --------------


def test_apply_refused_without_confirm_import_flag(db_session: Session) -> None:
    service = OdooCatalogueImportService(db_session)

    with pytest.raises(ImportBlockedError, match="confirm-import"):
        service.run_apply(
            confirmed=False, allow_partial=False, initiated_by="test", correlation_id="corr-1"
        )

    assert _table_count(db_session, "odoo_catalogue_import_runs") == 0


def test_apply_refused_when_blocking_approvals_unresolved(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Phase 6 approved D03/D04/D08/D09/D10/D19 in the real, committed approval file,
    # so this refusal path is now exercised against a monkeypatched, still-unresolved
    # approval set instead of the real file (which is expected to gate cleanly).
    monkeypatch.setattr(
        service_module,
        "load_business_approvals",
        lambda: [
            _approval("D03", status="PROPOSED"),
            _approval("D04", status="PROPOSED"),
            _approval("D08", status="PROPOSED"),
            _approval("D09", status="APPROVED", approved_value={"odoo_uom_id": 1}),
            _approval("D10", status="PROPOSED"),
            _approval("D19", status="PROPOSED"),
        ],
    )
    service = OdooCatalogueImportService(db_session)

    with pytest.raises(ImportBlockedError, match="unresolved"):
        service.run_apply(
            confirmed=True, allow_partial=False, initiated_by="test", correlation_id="corr-1"
        )

    assert _table_count(db_session, "odoo_catalogue_import_runs") == 0


def test_apply_proceeds_past_approval_gate_with_real_approval_file(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real, committed approval file has D03/D04/D08/D09/D10/D19 all APPROVED
    (Phase 6) — apply should get past the approval gate and reach the Odoo-connection
    check, not raise an "unresolved approvals" error. _connect() is monkeypatched to
    a deterministic "unavailable" result so this test's outcome never depends on
    whether a real Odoo instance happens to be reachable in the environment it runs in.
    """
    monkeypatch.setattr(
        service_module, "_connect", lambda: (None, "simulated: Odoo unavailable in this test")
    )
    service = OdooCatalogueImportService(db_session)

    with pytest.raises(ImportBlockedError, match="Cannot apply"):
        service.run_apply(
            confirmed=True, allow_partial=False, initiated_by="test", correlation_id="corr-1"
        )

    assert _table_count(db_session, "odoo_catalogue_import_runs") == 0


def test_apply_refused_when_all_items_blocked_and_allow_partial_not_set(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(monkeypatch)
    monkeypatch.setattr(
        service_module,
        "load_business_approvals",
        lambda: [
            _approval("D03", status="APPROVED", approved_value=["CUP"]),
            _approval("D04", status="APPROVED", approved_value="TB-<CAT>-<SEQ>"),
            # D08/D10/D19 deliberately left unapproved AND non-blocking here so the
            # approval *gate* itself passes, while the resulting plan still contains
            # BLOCKED product items (D08/D10/D19 still gate product-level planning in
            # odoo_import_planning.PRODUCT_BLOCKING_DECISION_IDS regardless of
            # blocks_import on the approval row) — isolates "gate passed, plan still
            # has blocked items" from "gate itself failed" (already covered above).
            _approval("D08", status="PROPOSED", blocks=False),
            _approval("D09", status="APPROVED", approved_value={"odoo_uom_id": 1}),
            _approval("D10", status="PROPOSED", blocks=False),
            _approval("D19", status="PROPOSED", blocks=False),
        ],
    )

    service = OdooCatalogueImportService(db_session)
    with pytest.raises(ImportBlockedError, match="BLOCKED"):
        service.run_apply(
            confirmed=True, allow_partial=False, initiated_by="test", correlation_id="corr-1"
        )

    assert _table_count(db_session, "odoo_catalogue_import_runs") == 0


# -- --dry-run ------------------------------------------------------------------------------


def test_dry_run_persists_run_and_items_without_any_odoo_write(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _fake_connected_client(monkeypatch)

    service = OdooCatalogueImportService(db_session)
    plan, run = service.run_dry_run(initiated_by="test", correlation_id="corr-dry-run")

    assert run.mode == "DRY_RUN"
    assert run.status == "SUCCEEDED"
    assert transport.write_call_count() == 0

    # Real canonical catalogue: 6 categories + 26 product templates + 6 attributes
    # (Pack Size, Box Size, Gift Tier, Cake Size, Ice Cream Size, Flavor) + 15
    # attribute values + 55 variant combinations (51 from the 25 category-default-size
    # products + 4 buttercream-cake size x flavor) = 108 planned items.
    assert len(plan.category_items) == 6
    assert len(plan.product_items) == 102  # 26 templates + 6 attrs + 15 values + 55 variants

    item_count = db_session.execute(
        text("SELECT count(*) FROM odoo_catalogue_import_items WHERE import_run_id = :run_id"),
        {"run_id": run.id},
    ).scalar_one()
    assert item_count == 108


def test_dry_run_run_id_is_a_real_uuid(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_connected_client(monkeypatch)
    service = OdooCatalogueImportService(db_session)

    _, run = service.run_dry_run(initiated_by="test", correlation_id="corr-1")

    assert isinstance(run.id, uuid.UUID)


# -- --validate -----------------------------------------------------------------------------


def test_validate_reports_odoo_unreachable_without_raising(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_module, "_connect", lambda: (None, "Odoo is not configured (test)"))

    service = OdooCatalogueImportService(db_session)
    report = service.run_validate()

    assert report.ok is False
    assert any("Odoo" in issue for issue in report.issues)
    # --validate never writes a run row, even on failure.
    assert _table_count(db_session, "odoo_catalogue_import_runs") == 0
