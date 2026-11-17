"""The critical duplicate scenario, against a fake Odoo that behaves like the real one: the
create commits on the server, and only then does the client see a timeout."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.integrations.odoo import order_push
from app.integrations.odoo.exceptions import (
    OdooConfigurationError,
    OdooConnectionError,
    OdooRemoteError,
    OdooTimeoutError,
    OdooWriteNotAllowedError,
)
from app.integrations.odoo.order_push import LiveOdooOrderPusher, OdooOrderLine
from app.integrations.odoo.write_target_guard import assert_odoo_write_target_approved


class FakeOdoo:
    def __init__(self) -> None:
        self.session = SimpleNamespace(database="db", uid=2)
        self.config = SimpleNamespace(credential="secret")
        self._transport = self
        self.sale_orders: list[dict[str, Any]] = []
        self.partners: list[dict[str, Any]] = []
        self.timeout_after_next_create = False
        self.fail_searches = False
        self.fail_confirms = 0
        # The next N sale.order lookups miss, as when a create is still committing.
        self.blind_lookups = 0
        # The next create loses a race: another worker commits the same key first.
        self.lose_next_race = False
        self.is_admin = False

    def search_read(self, model: str, domain: list[Any], fields: Any = None, **_: Any) -> Any:
        if self.fail_searches:
            raise OdooConnectionError("unreachable")
        if model == "sale.order":
            if self.blind_lookups:
                self.blind_lookups -= 1
                return SimpleNamespace(records=[])
            key = domain[1][2]
            found = [o for o in self.sale_orders if o["tb_order_key"] == key]
            return SimpleNamespace(records=found)
        if model == "product.pricelist":
            return SimpleNamespace(records=[{"id": 3}])
        if model == "account.tax":
            return SimpleNamespace(records=[{"id": 5}])
        if model == "product.product":
            return SimpleNamespace(records=[{"id": 77}])
        if model == "res.partner":
            return SimpleNamespace(records=[{"id": p["id"]} for p in self.partners])
        raise AssertionError(model)

    def read(
        self, model: str, ids: list[int], fields: Any = None, **_: Any
    ) -> list[dict[str, Any]]:
        if model == "sale.order":
            return [
                {
                    "amount_untaxed": 43.48,
                    "amount_tax": 6.52,
                    "amount_total": 50.0,
                    "currency_id": [1, "SAR"],
                    "order_line": [1],
                }
            ]
        return [
            {
                "id": 1,
                "product_id": [77, "Cake"],
                "product_uom_qty": 1.0,
                "price_unit": 50.0,
                "tax_ids": [5],
            }
        ]

    def call(self, _service: str, _method: str, args: list[Any], **_: Any) -> Any:
        model, method, call_args = args[3], args[4], args[5]
        if model == "res.partner" and method == "create":
            self.partners.append({"id": len(self.partners) + 1})
            return self.partners[-1]["id"]
        if model == "res.users" and method == "has_group":
            return self.is_admin
        if model == "sale.order" and method == "create":
            order = {"id": 100 + len(self.sale_orders), "state": "draft", **call_args[0]}
            # What the UNIQUE index does: one key, one row, whoever arrives second is rejected.
            if self.lose_next_race:
                self.lose_next_race = False
                self.sale_orders.append(order)
                raise OdooRemoteError("A sale order already exists for this storefront order.")
            if any(o["tb_order_key"] == order["tb_order_key"] for o in self.sale_orders):
                raise OdooRemoteError("A sale order already exists for this storefront order.")
            self.sale_orders.append(order)
            if self.timeout_after_next_create:
                self.timeout_after_next_create = False
                raise OdooTimeoutError("timed out")
            return order["id"]
        if model == "sale.order" and method == "action_confirm":
            if self.fail_confirms:
                self.fail_confirms -= 1
                raise OdooConnectionError("connection lost")
            for order in self.sale_orders:
                if order["id"] in call_args[0]:
                    order["state"] = "sale"
            return True
        raise AssertionError((model, method))


@pytest.fixture
def odoo(monkeypatch: pytest.MonkeyPatch) -> FakeOdoo:
    fake = FakeOdoo()
    monkeypatch.setattr(order_push, "_connect", lambda: fake)
    return fake


def _push() -> Any:
    return LiveOdooOrderPusher().push_order(
        order_number="TB-1",
        total_amount=50.0,
        tax_amount=6.52,
        discount_amount=0.0,
        delivery_fee_amount=0.0,
        promo_code=None,
        currency="SAR",
        customer_name="Sara",
        customer_phone="+966500000000",
        lines=[OdooOrderLine(sku="SKU", name_en="Cake", quantity=1, unit_price=50.0)],
    )


def _time_out_while_still_committing(odoo: FakeOdoo) -> None:
    """The lookup before the create and the recovery lookup after it both miss."""
    odoo.timeout_after_next_create = True
    odoo.blind_lookups = 2


def test_a_timeout_after_odoo_committed_never_creates_a_second_order(odoo: FakeOdoo) -> None:
    _time_out_while_still_committing(odoo)

    first = _push()
    assert first.success is False
    assert len(odoo.sale_orders) == 1

    second = _push()

    assert second.success is True
    assert second.odoo_sale_order_id == odoo.sale_orders[0]["id"]
    assert len(odoo.sale_orders) == 1


def test_a_timeout_is_recovered_at_once_when_the_order_is_already_visible(odoo: FakeOdoo) -> None:
    odoo.timeout_after_next_create = True

    result = _push()

    assert result.success is True
    assert result.odoo_sale_order_id == odoo.sale_orders[0]["id"]
    assert odoo.sale_orders[0]["state"] == "sale"


def test_losing_a_race_reuses_the_winning_order(odoo: FakeOdoo) -> None:
    odoo.lose_next_race = True

    result = _push()

    assert result.success is True
    assert result.raw["reused_existing"] is True
    assert result.odoo_sale_order_id == odoo.sale_orders[0]["id"]
    assert len(odoo.sale_orders) == 1


def test_the_unique_key_rejects_a_duplicate_even_when_every_lookup_misses(odoo: FakeOdoo) -> None:
    assert _push().success is True
    # Both lookups blind: the client-side check is gone, and only the index is left.
    odoo.blind_lookups = 2

    result = _push()

    assert result.success is False
    assert len(odoo.sale_orders) == 1


def test_a_retry_confirms_an_order_the_failed_attempt_left_in_draft(odoo: FakeOdoo) -> None:
    _time_out_while_still_committing(odoo)
    _push()
    assert odoo.sale_orders[0]["state"] == "draft"

    _push()

    assert odoo.sale_orders[0]["state"] == "sale"


def test_a_failed_confirmation_is_retried_rather_than_reported_as_synced(odoo: FakeOdoo) -> None:
    odoo.fail_confirms = 1

    first = _push()
    assert first.success is False
    assert first.raw["error"] == "sale_order_confirm_failed"
    assert odoo.sale_orders[0]["state"] == "draft"

    second = _push()

    assert second.success is True
    assert odoo.sale_orders[0]["state"] == "sale"
    assert len(odoo.sale_orders) == 1


@pytest.mark.parametrize(("is_admin", "refused"), [(True, True), (False, False)])
def test_an_administrator_account_is_refused(is_admin: bool, refused: bool) -> None:
    fake = FakeOdoo()
    fake.is_admin = is_admin

    if refused:
        with pytest.raises(OdooConfigurationError):
            order_push._refuse_administrator(fake)  # noqa: SLF001
    else:
        order_push._refuse_administrator(fake)  # noqa: SLF001


def test_nothing_is_created_when_the_duplicate_check_cannot_run(odoo: FakeOdoo) -> None:
    odoo.fail_searches = True

    with pytest.raises(OdooConnectionError):
        _push()

    assert odoo.sale_orders == []


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "odoo_base_url": "http://terrific-odoo:8069",
        "odoo_database": "terrific_odoo",
        "odoo_write_approved_target": "http://terrific-odoo:8069#terrific_odoo",
    }
    values.update(overrides)
    return Settings(**values)


def test_the_approved_target_may_be_written() -> None:
    assert_odoo_write_target_approved(_settings())


@pytest.mark.parametrize(
    "overrides",
    [
        {"odoo_write_approved_target": ""},
        {"odoo_base_url": "https://odoo.example.com"},
        {"odoo_database": "production"},
    ],
)
def test_any_other_target_is_refused(overrides: dict[str, str]) -> None:
    with pytest.raises(OdooWriteNotAllowedError):
        assert_odoo_write_target_approved(_settings(**overrides))


def _integration(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "deployment_stage": "local_integration",
        "odoo_order_push_provider": "live",
    }
    values.update(overrides)
    return _settings(**values)


def test_local_integration_accepts_the_isolated_stack() -> None:
    assert _integration().is_demo_stage is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_env": "production"},
        {"payment_provider": "tap"},
        {"notification_provider": "twilio"},
        {"odoo_order_push_provider": "stub"},
        {"odoo_base_url": "https://odoo.example.com"},
    ],
)
def test_local_integration_refuses_anything_unsafe(overrides: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        _integration(**overrides)
