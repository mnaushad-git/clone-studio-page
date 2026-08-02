from __future__ import annotations

import uuid

import pytest

from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooWriteNotAllowedError
from app.integrations.odoo.write_client import (
    EXPLICITLY_FORBIDDEN_METHODS,
    WRITE_ALLOWED_OPERATIONS,
    ImportExecutionContext,
    OdooWriteClient,
    WriteAudit,
)
from tests.unit.odoo.conftest import FakeTransport


def _context(**overrides: object) -> ImportExecutionContext:
    defaults: dict[str, object] = {
        "run_id": uuid.uuid4(),
        "correlation_id": "corr-1",
        "initiated_by": "test-suite",
        "mode": "APPLY",
    }
    defaults.update(overrides)
    return ImportExecutionContext(**defaults)  # type: ignore[arg-type]


def _authenticated_write_client(
    config: OdooConfig, transport: FakeTransport, context: ImportExecutionContext
) -> OdooWriteClient:
    transport.queue(("common", "authenticate"), 7)
    write_client = OdooWriteClient(config, transport, context)
    write_client.authenticate()
    return write_client


def test_invalid_mode_raises_at_construction() -> None:
    with pytest.raises(ValueError, match="Invalid import mode"):
        _context(mode="APPLY_FOREVER")


@pytest.mark.parametrize("mode", ["VALIDATE", "PLAN", "DRY_RUN", "ROLLBACK_PLAN"])
def test_write_refused_outside_apply_mode(
    config: OdooConfig, transport: FakeTransport, mode: str
) -> None:
    write_client = _authenticated_write_client(config, transport, _context(mode=mode))

    with pytest.raises(OdooWriteNotAllowedError, match="not APPLY"):
        write_client.create(
            "product.category",
            {"name": "Cupcakes"},
            audit=WriteAudit(
                entity_type="CATEGORY",
                canonical_external_key="cat.cupcakes",
                planned_operation="CREATE",
            ),
        )
    assert transport.write_call_count() == 0


@pytest.mark.parametrize("model_method", sorted(WRITE_ALLOWED_OPERATIONS))
def test_allowlisted_operations_are_permitted(
    config: OdooConfig, transport: FakeTransport, model_method: tuple[str, str]
) -> None:
    model, method = model_method
    write_client = _authenticated_write_client(config, transport, _context())
    transport.queue(("execute_kw", model, method), 42)

    audit = WriteAudit(
        entity_type="CATEGORY", canonical_external_key="k", planned_operation="CREATE"
    )
    if method == "create":
        result = write_client.create(model, {"name": "x"}, audit=audit)
        assert result == 42
    else:
        result = write_client.write(model, [1], {"name": "x"}, audit=audit)
        assert result is True  # write() coerces the truthy FakeTransport result to bool


@pytest.mark.parametrize("method", sorted(EXPLICITLY_FORBIDDEN_METHODS))
def test_explicitly_forbidden_methods_always_rejected(
    config: OdooConfig, transport: FakeTransport, method: str
) -> None:
    write_client = _authenticated_write_client(config, transport, _context())
    audit = WriteAudit(
        entity_type="CATEGORY", canonical_external_key="k", planned_operation="CREATE"
    )

    with pytest.raises(OdooWriteNotAllowedError, match="WRITE_ALLOWED_OPERATIONS"):
        write_client._execute_write("product.category", method, [[1]], audit=audit)  # noqa: SLF001
    assert transport.write_call_count() == 0


@pytest.mark.parametrize(
    "model,method",
    [
        ("stock.quant", "create"),
        ("account.tax", "create"),
        ("uom.uom", "create"),
        ("product.pricelist", "create"),
        ("res.company", "write"),
        ("ir.module.module", "write"),
        ("res.users", "write"),
        ("ir.model.access", "write"),
        ("product.category", "unlink"),
        ("product.template", "action_archive"),
    ],
)
def test_non_allowlisted_model_method_pairs_rejected(
    config: OdooConfig, transport: FakeTransport, model: str, method: str
) -> None:
    write_client = _authenticated_write_client(config, transport, _context())
    audit = WriteAudit(
        entity_type="CATEGORY", canonical_external_key="k", planned_operation="CREATE"
    )

    with pytest.raises(OdooWriteNotAllowedError):
        write_client._execute_write(model, method, [[1]], audit=audit)  # noqa: SLF001
    assert transport.write_call_count() == 0


def test_update_without_before_state_is_rejected(
    config: OdooConfig, transport: FakeTransport
) -> None:
    write_client = _authenticated_write_client(config, transport, _context())
    audit = WriteAudit(
        entity_type="CATEGORY",
        canonical_external_key="k",
        planned_operation="UPDATE",
        before_state=None,
    )

    with pytest.raises(OdooWriteNotAllowedError, match="before_state"):
        write_client.write("product.category", [1], {"name": "x"}, audit=audit)
    assert transport.write_call_count() == 0


def test_update_with_before_state_is_permitted(
    config: OdooConfig, transport: FakeTransport
) -> None:
    write_client = _authenticated_write_client(config, transport, _context())
    transport.queue(("execute_kw", "product.category", "write"), True)
    audit = WriteAudit(
        entity_type="CATEGORY",
        canonical_external_key="k",
        planned_operation="UPDATE",
        before_state={"name": "Old Name"},
    )

    assert write_client.write("product.category", [1], {"name": "New Name"}, audit=audit) is True


def test_create_call_shape_matches_odoo_execute_kw(
    config: OdooConfig, transport: FakeTransport
) -> None:
    write_client = _authenticated_write_client(config, transport, _context())
    transport.queue(("execute_kw", "product.category", "create"), 99)
    audit = WriteAudit(
        entity_type="CATEGORY", canonical_external_key="k", planned_operation="CREATE"
    )

    result = write_client.create("product.category", {"name": "Cupcakes"}, audit=audit)

    assert result == 99
    call = transport.calls[-1]
    assert call.service == "object"
    assert call.method == "execute_kw"
    database, uid, credential, model, odoo_method, args, kwargs = call.args
    assert database == config.database
    assert uid == 7
    assert credential == config.credential
    assert model == "product.category"
    assert odoo_method == "create"
    assert args == [{"name": "Cupcakes"}]
    assert kwargs == {}
    assert call.retryable is False  # writes are never blindly retried
    assert call.correlation_id == "corr-1"


def test_no_odoo_call_happens_before_gates_pass(
    config: OdooConfig, transport: FakeTransport
) -> None:
    """Constructing an OdooWriteClient and even calling .create() in a non-APPLY
    context must never reach the transport at all — the gate check happens before
    any network call is attempted.
    """
    write_client = _authenticated_write_client(config, transport, _context(mode="DRY_RUN"))
    audit = WriteAudit(
        entity_type="CATEGORY", canonical_external_key="k", planned_operation="CREATE"
    )

    with pytest.raises(OdooWriteNotAllowedError):
        write_client.create("product.category", {"name": "Cupcakes"}, audit=audit)

    assert len(transport.calls) == 1  # only the authenticate() call from the fixture setup
