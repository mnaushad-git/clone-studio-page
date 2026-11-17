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


def _queue_fiscal_setup(transport: FakeTransport) -> None:
    transport.queue(("execute_kw", "product.pricelist", "search_read"), [{"id": 3}])
    transport.queue(("execute_kw", "account.tax", "search_read"), [{"id": 5}])


def _queue_read_back(transport: FakeTransport, *, total: float = 22.0, tax: float = 2.87) -> None:
    transport.queue(
        ("execute_kw", "sale.order", "read"),
        [
            {
                "id": 501,
                "amount_untaxed": total - tax,
                "amount_tax": tax,
                "amount_total": total,
                "currency_id": [147, "SAR"],
                "order_line": [1],
            }
        ],
    )
    transport.queue(
        ("execute_kw", "sale.order.line", "read"),
        [
            {
                "id": 1,
                "product_id": [42, "Butter Frosting"],
                "product_uom_qty": 2.0,
                "price_unit": 11.0,
                "tax_ids": [5],
                "name": "Butter Frosting",
            }
        ],
    )


def _one_line() -> list[OdooOrderLine]:
    return [OdooOrderLine(sku="TB-CUP-003", name_en="Butter Frosting", quantity=2, unit_price=11.0)]


def test_creates_a_real_sale_order_for_an_existing_partner(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])  # no existing order
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])  # SKU resolves
    transport.queue(
        ("execute_kw", "res.partner", "search_read"), [{"id": 9}]
    )  # partner already exists
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    _queue_read_back(transport)
    transport.queue(("execute_kw", "sale.order", "action_confirm"), True)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
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
    assert values["pricelist_id"] == 3
    expected_line = {
        "product_id": 42,
        "product_uom_qty": 2,
        "price_unit": 11.0,
        "tax_ids": [(6, 0, [5])],
    }
    assert values["order_line"] == [(0, 0, expected_line)]


def test_creates_a_new_partner_when_none_matches_by_phone(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [])  # no existing partner
    transport.queue(("execute_kw", "res.partner", "create"), 77)
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    _queue_read_back(transport)
    transport.queue(("execute_kw", "sale.order", "action_confirm"), True)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
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
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    _queue_read_back(transport)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
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
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [])  # SKU not found

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
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
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(
        ("execute_kw", "sale.order", "create"),
        OdooValidationError("a required field is missing"),
    )

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert "required field is missing" in result.raw["error"]


def test_a_confirm_failure_is_reported_so_the_outbox_retries_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retry finds this order by its key and confirms it, so a draft is never "synced"."""
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    _queue_read_back(transport)
    transport.queue(
        ("execute_kw", "sale.order", "action_confirm"),
        OdooValidationError("nothing to invoice"),
    )

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert result.raw["error"] == "sale_order_confirm_failed"
    assert result.raw["sale_order_id"] == 501


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
            tax_amount=2.87,
            discount_amount=0.0,
            delivery_fee_amount=0.0,
            promo_code=None,
            currency="SAR",
            customer_name="Sara M.",
            customer_phone="+966500000000",
            lines=_one_line(),
        )


def test_a_sale_order_that_does_not_reconcile_is_left_in_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))

    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    _queue_fiscal_setup(transport)
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    _queue_read_back(transport, total=25.3, tax=3.3)  # Odoo added VAT on top

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=22.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert result.raw["error"] == "order_reconciliation_failed"
    assert result.raw["sale_order_id"] == 501
    assert any("total" in problem for problem in result.raw["discrepancies"])
    assert not any(
        c.method == "execute_kw" and c.args[3:5] == ["sale.order", "action_confirm"]
        for c in transport.calls
    )


def test_an_order_whose_own_figures_do_not_add_up_never_reaches_odoo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _must_not_connect() -> None:
        raise AssertionError("connected to Odoo")

    monkeypatch.setattr(order_push_module, "_connect", _must_not_connect)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=23.0,
        tax_amount=2.87,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=_one_line(),
    )

    assert result.success is False
    assert result.raw["error"] == "order_reconciliation_failed"


@pytest.mark.parametrize("model", ["product.pricelist", "account.tax"])
def test_missing_fiscal_setup_refuses_the_push(monkeypatch: pytest.MonkeyPatch, model: str) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))
    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    _queue_fiscal_setup(transport)
    transport._responses[("execute_kw", model, "search_read")] = [[]]  # noqa: SLF001

    with pytest.raises(OdooConfigurationError):
        LiveOdooOrderPusher().push_order(
            order_number="TB-ABC123",
            total_amount=22.0,
            tax_amount=2.87,
            discount_amount=0.0,
            delivery_fee_amount=0.0,
            promo_code=None,
            currency="SAR",
            customer_name="Sara M.",
            customer_phone="+966500000000",
            lines=_one_line(),
        )

    assert transport.write_call_count() == 0


def test_delivery_and_discount_are_their_own_taxed_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(order_push_module, "_connect", lambda: _connected_client(transport))
    transport.queue(("execute_kw", "sale.order", "search_read"), [])
    _queue_fiscal_setup(transport)
    # product SKU, then the discount product, then the delivery product
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 42}])
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 80}])
    transport.queue(("execute_kw", "product.product", "search_read"), [{"id": 81}])
    transport.queue(("execute_kw", "res.partner", "search_read"), [{"id": 9}])
    transport.queue(("execute_kw", "sale.order", "create"), 501)
    transport.queue(
        ("execute_kw", "sale.order", "read"),
        [
            {
                "amount_untaxed": 22.61,
                "amount_tax": 3.39,
                "amount_total": 26.0,
                "currency_id": [147, "SAR"],
                "order_line": [1, 2, 3],
            }
        ],
    )
    transport.queue(
        ("execute_kw", "sale.order.line", "read"),
        [
            {
                "id": 1,
                "product_id": [42, "x"],
                "product_uom_qty": 2,
                "price_unit": 11.0,
                "tax_ids": [5],
                "name": "Butter Frosting\nInscription: Hi",
            },  # noqa: E501
            {
                "id": 2,
                "product_id": [80, "x"],
                "product_uom_qty": 1,
                "price_unit": -4.0,
                "tax_ids": [5],
                "name": "Discount (SAVE)",
            },  # noqa: E501
            {
                "id": 3,
                "product_id": [81, "x"],
                "product_uom_qty": 1,
                "price_unit": 8.0,
                "tax_ids": [5],
                "name": "Delivery",
            },  # noqa: E501
        ],
    )
    transport.queue(("execute_kw", "sale.order", "action_confirm"), True)

    result = LiveOdooOrderPusher().push_order(
        order_number="TB-ABC123",
        total_amount=26.0,
        tax_amount=3.39,
        discount_amount=4.0,
        delivery_fee_amount=8.0,
        promo_code="SAVE",
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=[
            OdooOrderLine(
                sku="TB-CUP-003",
                name_en="Butter Frosting",
                quantity=2,
                unit_price=11.0,
                description="Butter Frosting\nInscription: Hi",
            )
        ],
    )

    assert result.success is True
    values = _find_call(transport, "sale.order", "create").args[5][0]
    lines = [line[2] for line in values["order_line"]]
    assert [line["product_id"] for line in lines] == [42, 80, 81]
    assert lines[0]["name"] == "Butter Frosting\nInscription: Hi"
    assert lines[1]["price_unit"] == -4.0
    assert lines[2]["price_unit"] == 8.0
