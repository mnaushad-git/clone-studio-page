"""LiveOdooOrderPusher against a FakeTransport — never a real Odoo instance, mirrors
test_odoo_import_service.py's approach (_connect() monkeypatched to hand back an
authenticated OdooClient over a fake transport pre-loaded with responses).
"""

from __future__ import annotations

import pytest

from app.integrations.odoo import order_push as order_push_module
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooValidationError
from app.integrations.odoo.order_push import LiveOdooOrderPusher, OdooOrderLine
from tests.unit.odoo.conftest import FakeTransport, RecordedCall, make_config


def _find_call(transport: FakeTransport, model: str, method: str) -> RecordedCall:
    return next(
        c
        for c in transport.calls
        if c.service == "object" and c.method == "execute_kw" and c.args[3:5] == [model, method]
    )


def _connected_client(transport: FakeTransport) -> OdooClient:
    config = make_config()
    transport.queue(("common", "version"), {"server_version": "19.0-test"})
    transport.queue(("common", "authenticate"), 7)
    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()
    return client


def _one_line() -> list[OdooOrderLine]:
    return [OdooOrderLine(sku="TB-CUP-003", name_en="Butter Frosting", quantity=2, unit_price=11.0)]


def test_creates_a_real_sale_order_for_an_existing_partner(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])  # no existing order
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])  # SKU resolves
    transport.queue(
        ("execute_kw", "res.partner", "search_read"), [{"id": 9}]
    )  # partner already exists
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    transport.queue(("execute_kw", "sale.order", "action_confirm"), True)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is True
    assert result.odoo_sale_order_id == 501
    assert result.raw["partner_id"] == 9
    assert transport.write_call_count() == 1  # sale.order create (action_confirm isn't CRUD)
    assert _find_call(transport, "sale.order", "action_confirm").args[5] == [[501]]

    values = _find_call(transport, "sale.order", "create").args[5][0]
    assert values["client_order_ref"] == "TB-ABC123"
    assert values["partner_id"] == 9
    expected_line = {"product_id": 42, "product_uom_qty": 2, "price_unit": 11.0}
    assert values["order_line"] == [(0, 0, expected_line)]


def test_creates_a_new_partner_when_none_matches_by_phone(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [])  # no existing partner
    transport.queue(("execute_kw", "res.partner", "create"), 77)
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    transport.queue(("execute_kw", "sale.order", "action_confirm"), True)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is True
    assert result.raw["partner_id"] == 77
    values = _find_call(transport, "res.partner", "create").args[5][0]
    assert values == {"name": "Sara M.", "phone": "+966500000000"}


def test_retry_reuses_the_existing_sale_order_instead_of_duplicating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [{"id": 999}])

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is True
    assert result.odoo_sale_order_id == 999
    assert result.raw["reused_existing"] is True
    assert transport.write_call_count() == 0  # nothing created — the existing order was reused


def test_a_sku_never_imported_into_odoo_fails_the_whole_push_without_any_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    transport.queue(("execute_kw", "product.product", "search_read"), [])  # SKU not found

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert result.raw["unresolved_skus"] == ["TB-CUP-003"]
    assert transport.write_call_count() == 0


def test_odoo_rejecting_the_sale_order_create_is_reported_as_a_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(
        ("execute_kw", "sale.order", "create"),
        OdooValidationError("a required field is missing"),
    )

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert "required field is missing" in result.raw["error"]


def test_a_confirm_failure_after_a_successful_create_is_still_reported_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sale.order itself was created — that's the part that must not be lost."""
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    transport.queue(
        ("execute_kw", "sale.order", "action_confirm"),
        OdooValidationError("nothing to invoice"),
    )

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is True
    assert result.odoo_sale_order_id == 501


def test_odoo_not_configured_raises_instead_of_returning_a_fake_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> None:
        raise OdooConfigurationError("Odoo is not configured")

    monkeypatch.setattr(order_push_module, "_connect", _boom)

    with pytest.raises(OdooConfigurationError):
        LiveOdooOrderPusher().push_order(
            order_number="TB-ABC123",
            total_amount=22.0,
            currency="SAR",
            customer_name="Sara M.",
            customer_phone="+966500000000",
            lines=_one_line(),
        )
