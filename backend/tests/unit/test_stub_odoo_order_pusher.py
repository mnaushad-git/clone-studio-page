from __future__ import annotations

from app.integrations.odoo.order_push import OdooOrderLine, StubOdooOrderPusher


def test_stub_pusher_always_succeeds_and_never_calls_a_real_odoo_instance() -> None:
    pusher = StubOdooOrderPusher()

    result = pusher.push_order(
        order_number="TB-ABC123",
        total_amount=58.15,
        tax_amount=7.58,
        discount_amount=0.0,
        delivery_fee_amount=10.21,
        promo_code=None,
        currency="SAR",
        customer_name="Sara M.",
        customer_phone="+966500000000",
        lines=[
            OdooOrderLine(sku="TB-CHO-009", name_en="Berry Truffle", quantity=6, unit_price=7.99)
        ],
    )

    assert result.success is True
    assert result.odoo_sale_order_id is None
    assert result.raw["note"] == "Stub pusher — no real Odoo call was made."
    assert result.raw["line_count"] == 1
