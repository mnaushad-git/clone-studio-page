"""Order → Odoo sale.order push boundary.

Two implementations: StubOdooOrderPusher (the Launch Sprint default — never opens a
connection to Odoo) and LiveOdooOrderPusher (writes a real sale.order). Selected via
ODOO_ORDER_PUSH_PROVIDER, see order_push_factory.py.

LiveOdooOrderPusher deliberately does not reuse app/integrations/odoo/write_client.py —
that class is a closed, catalogue-import-specific surface (its own docstring: "only the
Phase 5 catalogue importer constructs" it), gated to an ImportExecutionContext/APPLY mode
that has no sale-order equivalent. Reusing it here would mean either loosening its
allowlist for an unrelated caller or faking an import context, both worse than this
module owning its own small, self-contained write path (CLAUDE.md rule 6: Odoo-specific
logic stays isolated per adapter, not shared beyond what actually applies).

Idempotency (rule 7): before creating anything, push_order() searches for an existing
sale.order by client_order_ref == order_number. A retry (crash between a successful
create and the outbox event being marked completed, or an operator-triggered re-sync)
finds and reuses that record instead of creating a duplicate sale order.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooIntegrationError
from app.integrations.odoo.transport import OdooTransport

logger = logging.getLogger("app.integrations.odoo.order_push")


@dataclass(frozen=True)
class OdooOrderLine:
    sku: str
    name_en: str
    quantity: int
    unit_price: float
    odoo_variant_id: int | None = None


@dataclass(frozen=True)
class OdooPushResult:
    success: bool
    odoo_sale_order_id: int | None
    raw: dict[str, Any]


class OdooOrderPusher(Protocol):
    name: str

    def push_order(
        self,
        *,
        order_number: str,
        total_amount: float,
        currency: str,
        customer_name: str,
        customer_phone: str,
        lines: list[OdooOrderLine],
    ) -> OdooPushResult:
        """Push a paid order into Odoo as a sale order. Must never raise for a normal
        rejection — that's OdooPushResult(success=False, ...); only truly exceptional
        conditions (Odoo unreachable, malformed config) should raise.
        """
        ...


class StubOdooOrderPusher:
    """Never contacts Odoo. Returns a synthetic id so downstream code (order sync
    status, tests) can exercise the full success path without a real instance.
    """

    name = "stub"

    def push_order(
        self,
        *,
        order_number: str,
        total_amount: float,
        currency: str,
        customer_name: str,
        customer_phone: str,
        lines: list[OdooOrderLine],
    ) -> OdooPushResult:
        return OdooPushResult(
            success=True,
            odoo_sale_order_id=None,
            raw={
                "provider": self.name,
                "note": "Stub pusher — no real Odoo call was made.",
                "correlation_id": f"stub-push-{uuid.uuid4().hex[:12]}",
                "order_number": order_number,
                "total_amount": total_amount,
                "currency": currency,
                "line_count": len(lines),
            },
        )


def _connect() -> OdooClient:
    """Raises OdooIntegrationError (or a subclass) on any connectivity/config/auth
    failure — allowed per the protocol's contract ("only truly exceptional conditions
    ... should raise"); the sync service already treats a raised exception from
    push_order() the same as a returned failure (odoo_sync_service.py._process_event).
    """
    from app.core.config import get_settings

    settings = get_settings()
    if not OdooConfig.is_configured(settings):
        raise OdooConfigurationError(
            "Odoo is not configured (ODOO_BASE_URL/DATABASE/USERNAME empty) — cannot "
            "push an order with ODOO_ORDER_PUSH_PROVIDER=live"
        )
    config = OdooConfig.from_settings(settings)
    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()
    return client


def _call_write(client: OdooClient, model: str, method: str, args: list[Any]) -> Any:
    """The one write choke point for this module — mirrors OdooWriteClient's own
    _execute_write shape (same call_args layout, same retryable=False rationale: a
    failed create could have partially succeeded server-side, so this module decides
    recovery itself via the client_order_ref idempotency check, never a blind retry).
    Deliberately reaches past OdooClient's read-only gate via its transport, the same
    idiom app/services/catalogue/odoo_import_service.py uses to hand OdooClient's
    transport to a write-capable caller.
    """
    session = client.session
    call_args = [session.database, session.uid, client.config.credential, model, method, args, {}]
    return client._transport.call(  # noqa: SLF001
        "object", "execute_kw", call_args, retryable=False, correlation_id=None
    )


def _find_or_create_partner(client: OdooClient, *, name: str, phone: str) -> int:
    try:
        found = client.search_read(
            "res.partner", ["|", ["phone", "=", phone], ["mobile", "=", phone]], ["id"], limit=1
        )
    except OdooIntegrationError:
        # res.partner.mobile isn't guaranteed to exist on every Odoo version/instance
        # (e.g. absent on this deployment's Odoo 19) — fall back to phone-only rather
        # than failing every order push over an optional field.
        found = client.search_read("res.partner", [["phone", "=", phone]], ["id"], limit=1)
    if found.records:
        return int(found.records[0]["id"])
    new_id = _call_write(client, "res.partner", "create", [{"name": name, "phone": phone}])
    return int(new_id)


class LiveOdooOrderPusher:
    """Creates (or, on retry, reuses) a real Odoo sale.order per paid order. Each cart
    line is resolved against product.product by SKU (product.template.default_code,
    set by the catalogue importer — app/services/catalogue/odoo_import_service.py) — an
    order referencing a SKU that was never imported into Odoo fails the whole push
    (OdooPushResult(success=False, ...)) rather than silently creating a partial order.
    """

    name = "live"

    def push_order(
        self,
        *,
        order_number: str,
        total_amount: float,
        currency: str,
        customer_name: str,
        customer_phone: str,
        lines: list[OdooOrderLine],
    ) -> OdooPushResult:
        client = _connect()

        existing = client.search_read(
            "sale.order", [["client_order_ref", "=", order_number]], ["id"], limit=1
        )
        if existing.records:
            sale_order_id = int(existing.records[0]["id"])
            logger.info(
                "odoo_order_push_reused_existing",
                extra={"order_number": order_number, "sale_order_id": sale_order_id},
            )
            return OdooPushResult(
                success=True,
                odoo_sale_order_id=sale_order_id,
                raw={"provider": self.name, "reused_existing": True},
            )

        order_lines: list[tuple[int, int, dict[str, Any]]] = []
        unresolved_skus: list[str] = []
        for line in lines:
            # Prefer the already-resolved Odoo variant id (set once the catalogue
            # importer's variant pass has run — see odoo_import_service.py's
            # _apply_variant_item) over a live default_code search: it's the specific
            # size/flavor combination the customer picked, not just whichever
            # product.product happens to share the line's SKU, and it avoids a round
            # trip per line in the common case.
            if line.odoo_variant_id is not None:
                product_id = line.odoo_variant_id
            else:
                variants = client.search_read(
                    "product.product", [["default_code", "=", line.sku]], ["id"], limit=1
                )
                if not variants.records:
                    unresolved_skus.append(line.sku)
                    continue
                product_id = int(variants.records[0]["id"])
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product_id,
                        "product_uom_qty": line.quantity,
                        "price_unit": line.unit_price,
                    },
                )
            )

        if unresolved_skus:
            logger.warning(
                "odoo_order_push_unresolved_skus",
                extra={"order_number": order_number, "unresolved_skus": unresolved_skus},
            )
            return OdooPushResult(
                success=False,
                odoo_sale_order_id=None,
                raw={
                    "provider": self.name,
                    "error": "sku_not_found_in_odoo",
                    "unresolved_skus": unresolved_skus,
                },
            )

        try:
            partner_id = _find_or_create_partner(client, name=customer_name, phone=customer_phone)
            sale_order_id = int(
                _call_write(
                    client,
                    "sale.order",
                    "create",
                    [
                        {
                            "partner_id": partner_id,
                            "client_order_ref": order_number,
                            "order_line": order_lines,
                        }
                    ],
                )
            )
        except OdooIntegrationError as exc:
            logger.exception("odoo_order_push_failed", extra={"order_number": order_number})
            return OdooPushResult(
                success=False,
                odoo_sale_order_id=None,
                raw={"provider": self.name, "error": str(exc)},
            )

        try:
            _call_write(client, "sale.order", "action_confirm", [[sale_order_id]])
        except OdooIntegrationError:
            # The sale.order itself was created successfully — that's the part that
            # must not be lost. Confirmation (draft quotation -> confirmed order) is a
            # cosmetic nicety on top; log and move on rather than fail an otherwise-
            # successful push over it.
            logger.warning(
                "odoo_sale_order_confirm_failed",
                extra={"order_number": order_number, "sale_order_id": sale_order_id},
            )

        logger.info(
            "odoo_order_push_succeeded",
            extra={
                "order_number": order_number,
                "sale_order_id": sale_order_id,
                "partner_id": partner_id,
                "line_count": len(order_lines),
            },
        )
        return OdooPushResult(
            success=True,
            odoo_sale_order_id=sale_order_id,
            raw={"provider": self.name, "partner_id": partner_id, "line_count": len(order_lines)},
        )
