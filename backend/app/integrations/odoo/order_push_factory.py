from __future__ import annotations

from app.core.config import Settings
from app.integrations.odoo.order_push import (
    LiveOdooOrderPusher,
    OdooOrderPusher,
    StubOdooOrderPusher,
)

_PUSHERS: dict[str, type[OdooOrderPusher]] = {
    "stub": StubOdooOrderPusher,
    "live": LiveOdooOrderPusher,
}


def get_odoo_order_pusher(settings: Settings) -> OdooOrderPusher:
    pusher_cls = _PUSHERS.get(settings.odoo_order_push_provider)
    if pusher_cls is None:
        raise ValueError(
            f"Unknown ODOO_ORDER_PUSH_PROVIDER {settings.odoo_order_push_provider!r} — "
            f"expected one of {sorted(_PUSHERS)}."
        )
    return pusher_cls()
