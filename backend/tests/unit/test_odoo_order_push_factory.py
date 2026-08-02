from __future__ import annotations

import pytest

from app.core.config import Settings
from app.integrations.odoo.order_push import StubOdooOrderPusher
from app.integrations.odoo.order_push_factory import get_odoo_order_pusher


def test_default_settings_resolve_to_the_stub_pusher() -> None:
    pusher = get_odoo_order_pusher(Settings())

    assert isinstance(pusher, StubOdooOrderPusher)


def test_unknown_odoo_order_push_provider_raises_instead_of_silently_falling_back() -> None:
    settings = Settings(odoo_order_push_provider="some_future_odoo_adapter")

    with pytest.raises(ValueError, match="some_future_odoo_adapter"):
        get_odoo_order_pusher(settings)
