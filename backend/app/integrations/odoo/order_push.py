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

Idempotency (rule 7) is enforced by Odoo, not by this client: the terrific_order_sync addon
(deploy/odoo/addons) adds sale.order.tb_order_key with a UNIQUE index, and every create sets
it to the order number. However many workers race, or however a timed-out create turns out,
PostgreSQL commits at most one sale order per key. The lookup before creating and the one
after a failed create only decide whether to reuse that order; neither is the safeguard.

Financial agreement is enforced before confirming: every order goes in on the SAR pricelist
with the VAT-inclusive tax set on each line, delivery and discount as their own lines, and
is read back and compared with the storefront's figures (order_reconciliation.py). An order
that doesn't match stays in draft and the push reports failure. VAT treatment and delivery
tax are proposed rules awaiting client finance approval, see docs/integrations/
odoo-order-financials.md.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooIntegrationError
from app.integrations.odoo.order_reconciliation import (
    ExpectedLine,
    ExpectedOrder,
    find_discrepancies,
    storefront_arithmetic_problem,
    to_cents,
)
from app.integrations.odoo.transport import OdooTransport
from app.integrations.odoo.write_target_guard import assert_odoo_write_target_approved

logger = logging.getLogger("app.integrations.odoo.order_push")

ORDER_KEY_FIELD = "tb_order_key"
# Service products created by deploy/odoo/bootstrap.py.
DELIVERY_PRODUCT_CODE = "TB-DELIVERY-FEE"
DISCOUNT_PRODUCT_CODE = "TB-PROMO-DISCOUNT"


@dataclass(frozen=True)
class OdooOrderLine:
    sku: str
    name_en: str
    quantity: int
    unit_price: float
    odoo_variant_id: int | None = None
    # What the customer chose (variant axes, inscription). Becomes the sale line description.
    description: str | None = None


@dataclass(frozen=True)
class OdooPushResult:
    success: bool
    odoo_sale_order_id: int | None
    raw: dict[str, Any]
    # True when nothing was actually sent to Odoo. Recorded as odoo_sync_status="simulated".
    simulated: bool = False


class OdooOrderPusher(Protocol):
    name: str

    def push_order(
        self,
        *,
        order_number: str,
        total_amount: float,
        tax_amount: float,
        discount_amount: float,
        delivery_fee_amount: float,
        promo_code: str | None,
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
        tax_amount: float,
        discount_amount: float,
        delivery_fee_amount: float,
        promo_code: str | None,
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
            simulated=True,
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
    assert_odoo_write_target_approved(settings)
    config = OdooConfig.from_settings(settings)
    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()
    _refuse_administrator(client)
    return client


def _refuse_administrator(client: OdooClient) -> None:
    uid = client.session.uid
    if _call_write(client, "res.users", "has_group", [[uid], "base.group_system"]):
        raise OdooConfigurationError(
            "The Odoo account used for order sync has administrator rights. Use the dedicated "
            "order sync user created by deploy/odoo/bootstrap.py."
        )


def _call_write(client: OdooClient, model: str, method: str, args: list[Any]) -> Any:
    """The one write choke point for this module — mirrors OdooWriteClient's own
    _execute_write shape (same call_args layout, same retryable=False rationale: a
    failed create could have partially succeeded server-side, so this module decides
    recovery itself via the tb_order_key unique index, never a blind retry).
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


@dataclass(frozen=True)
class OdooFiscalSetup:
    pricelist_id: int
    tax_id: int


def _exactly_one(client: OdooClient, model: str, domain: list[Any], what: str) -> int:
    records = client.search_read(model, domain, ["id"], limit=2).records
    if len(records) != 1:
        raise OdooConfigurationError(
            f"Expected exactly one {what} in Odoo, found {len(records)}. "
            "Run deploy/odoo/bootstrap.py against this database."
        )
    return int(records[0]["id"])


def _resolve_fiscal_setup(client: OdooClient, currency: str) -> OdooFiscalSetup:
    """Refuses to push rather than let Odoo fall back to its own default pricelist or tax."""
    from app.core.config import get_settings

    rate = get_settings().checkout_tax_rate_percent
    return OdooFiscalSetup(
        pricelist_id=_exactly_one(
            client,
            "product.pricelist",
            [["currency_id.name", "=", currency], ["active", "=", True]],
            f"active {currency} pricelist",
        ),
        tax_id=_exactly_one(
            client,
            "account.tax",
            [
                ["type_tax_use", "=", "sale"],
                ["amount", "=", rate],
                ["price_include_override", "=", "tax_included"],
                ["active", "=", True],
            ],
            f"active price-included {rate:g}% sale tax",
        ),
    )


def _one_product(client: OdooClient, code: str) -> int:
    return _exactly_one(client, "product.product", [["default_code", "=", code]], f"{code} product")


def _delivery_vat_applies() -> bool:
    from app.core.config import get_settings

    return get_settings().checkout_delivery_vat_applies


def _line_values(line: ExpectedLine) -> dict[str, Any]:
    values: dict[str, Any] = {
        "product_id": line.product_id,
        "product_uom_qty": line.quantity,
        "price_unit": line.unit_price,
        # Set on every line so a product's own tax setting can't change what was charged.
        "tax_ids": [(6, 0, list(line.tax_ids))],
    }
    if line.name is not None:
        values["name"] = line.name
    return values


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
        tax_amount: float,
        discount_amount: float,
        delivery_fee_amount: float,
        promo_code: str | None,
        currency: str,
        customer_name: str,
        customer_phone: str,
        lines: list[OdooOrderLine],
    ) -> OdooPushResult:
        problem = storefront_arithmetic_problem(
            line_amounts=[(line.unit_price, line.quantity) for line in lines],
            discount=discount_amount,
            delivery_fee=delivery_fee_amount,
            total=total_amount,
        )
        if problem:
            logger.error(
                "odoo_order_amounts_inconsistent",
                extra={"order_number": order_number, "problem": problem},
            )
            return self._reconciliation_failed(None, [problem])

        client = _connect()

        # Raises, creating nothing, if the addon is missing: the field is then unknown.
        existing = self._find_existing(client, order_number)

        setup = _resolve_fiscal_setup(client, currency)
        expected_lines, unresolved_skus = self._expected_lines(
            client,
            lines=lines,
            setup=setup,
            discount_amount=discount_amount,
            delivery_fee_amount=delivery_fee_amount,
            promo_code=promo_code,
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
        expected = ExpectedOrder(
            currency=currency, total=total_amount, tax=tax_amount, lines=tuple(expected_lines)
        )

        if existing is not None:
            return self._reuse(client, order_number, existing, expected)

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
                            ORDER_KEY_FIELD: order_number,
                            "pricelist_id": setup.pricelist_id,
                            "order_line": [(0, 0, _line_values(line)) for line in expected_lines],
                        }
                    ],
                )
            )
        except OdooIntegrationError as exc:
            # A unique-key rejection means another worker won, and a timeout may mean our
            # own create committed. Either way the order may now exist.
            return self._recover_failed_create(client, order_number, exc, expected)

        result = self._reconcile_and_confirm(client, order_number, sale_order_id, "draft", expected)
        if result.success:
            result.raw["partner_id"] = partner_id
            result.raw["line_count"] = len(expected_lines)
            logger.info(
                "odoo_order_push_succeeded",
                extra={
                    "order_number": order_number,
                    "sale_order_id": sale_order_id,
                    "partner_id": partner_id,
                    "line_count": len(expected_lines),
                },
            )
        return result

    def _expected_lines(
        self,
        client: OdooClient,
        *,
        lines: list[OdooOrderLine],
        setup: OdooFiscalSetup,
        discount_amount: float,
        delivery_fee_amount: float,
        promo_code: str | None,
    ) -> tuple[list[ExpectedLine], list[str]]:
        vat = (setup.tax_id,)
        expected: list[ExpectedLine] = []
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
            expected.append(
                ExpectedLine(product_id, line.quantity, line.unit_price, vat, line.description)
            )

        # The storefront's discount is on the whole order. A negative line keeps every
        # product at the price the customer saw and reproduces the VAT exactly.
        if to_cents(discount_amount) > 0:
            label = f"Discount ({promo_code})" if promo_code else "Discount"
            discount_product = _one_product(client, DISCOUNT_PRODUCT_CODE)
            expected.append(ExpectedLine(discount_product, 1, -discount_amount, vat, label))
        if to_cents(delivery_fee_amount) > 0:
            delivery_taxes = vat if _delivery_vat_applies() else ()
            delivery_product = _one_product(client, DELIVERY_PRODUCT_CODE)
            expected.append(
                ExpectedLine(delivery_product, 1, delivery_fee_amount, delivery_taxes, "Delivery")
            )
        return expected, unresolved_skus

    @staticmethod
    def _find_existing(client: OdooClient, order_number: str) -> dict[str, Any] | None:
        # The second branch finds orders pushed before the addon existed, which have no key.
        domain = [
            "|",
            [ORDER_KEY_FIELD, "=", order_number],
            "&",
            [ORDER_KEY_FIELD, "=", False],
            ["client_order_ref", "=", order_number],
        ]
        found = client.search_read("sale.order", domain, ["id", "state"], limit=1)
        return found.records[0] if found.records else None

    def _reuse(
        self,
        client: OdooClient,
        order_number: str,
        existing: dict[str, Any],
        expected: ExpectedOrder,
    ) -> OdooPushResult:
        sale_order_id = int(existing["id"])
        # The earlier attempt may have died between creating and confirming.
        result = self._reconcile_and_confirm(
            client, order_number, sale_order_id, existing.get("state", ""), expected
        )
        if result.success:
            result.raw["reused_existing"] = True
            logger.info(
                "odoo_order_push_reused_existing",
                extra={"order_number": order_number, "sale_order_id": sale_order_id},
            )
        return result

    def _reconcile_and_confirm(
        self,
        client: OdooClient,
        order_number: str,
        sale_order_id: int,
        state: str,
        expected: ExpectedOrder,
    ) -> OdooPushResult:
        try:
            order, problems = self._read_and_compare(client, sale_order_id, expected)
        except OdooIntegrationError as exc:
            order, problems = {}, [f"could not read the sale order back: {exc}"]
        if problems:
            logger.error(
                "odoo_order_reconciliation_failed",
                extra={
                    "order_number": order_number,
                    "sale_order_id": sale_order_id,
                    "discrepancies": problems,
                },
            )
            return self._reconciliation_failed(sale_order_id, problems)
        if state == "draft" and not self._confirm(client, order_number, sale_order_id):
            return self._confirm_failed(sale_order_id)
        return OdooPushResult(
            success=True,
            odoo_sale_order_id=sale_order_id,
            raw={
                "provider": self.name,
                "amount_untaxed": order.get("amount_untaxed"),
                "amount_tax": order.get("amount_tax"),
                "amount_total": order.get("amount_total"),
            },
        )

    @staticmethod
    def _read_and_compare(
        client: OdooClient, sale_order_id: int, expected: ExpectedOrder
    ) -> tuple[dict[str, Any], list[str]]:
        orders = client.read(
            "sale.order",
            [sale_order_id],
            ["amount_untaxed", "amount_tax", "amount_total", "currency_id", "order_line"],
        )
        if not orders:
            return {}, [f"sale order {sale_order_id} could not be read back"]
        order = orders[0]
        lines = client.read(
            "sale.order.line",
            order.get("order_line") or [],
            ["product_id", "product_uom_qty", "price_unit", "tax_ids", "name"],
        )
        return order, find_discrepancies(expected, order, lines)

    def _reconciliation_failed(
        self, sale_order_id: int | None, problems: list[str]
    ) -> OdooPushResult:
        return OdooPushResult(
            success=False,
            odoo_sale_order_id=None,
            raw={
                "provider": self.name,
                "error": "order_reconciliation_failed",
                "sale_order_id": sale_order_id,
                "discrepancies": problems,
            },
        )

    def _recover_failed_create(
        self,
        client: OdooClient,
        order_number: str,
        error: OdooIntegrationError,
        expected: ExpectedOrder,
    ) -> OdooPushResult:
        try:
            existing = self._find_existing(client, order_number)
        except OdooIntegrationError:
            existing = None
        if existing is not None:
            return self._reuse(client, order_number, existing, expected)
        logger.warning(
            "odoo_order_push_failed", extra={"order_number": order_number, "error": str(error)}
        )
        return OdooPushResult(
            success=False,
            odoo_sale_order_id=None,
            raw={"provider": self.name, "error": str(error)},
        )

    def _confirm_failed(self, sale_order_id: int) -> OdooPushResult:
        # Reported as a failure so that the outbox retries. The retry finds this order by
        # its key and confirms it, so nothing is created twice and a draft isn't marked synced.
        return OdooPushResult(
            success=False,
            odoo_sale_order_id=None,
            raw={
                "provider": self.name,
                "error": "sale_order_confirm_failed",
                "sale_order_id": sale_order_id,
            },
        )

    @staticmethod
    def _confirm(client: OdooClient, order_number: str, sale_order_id: int) -> bool:
        try:
            _call_write(client, "sale.order", "action_confirm", [[sale_order_id]])
        except OdooIntegrationError:
            logger.warning(
                "odoo_sale_order_confirm_failed",
                extra={"order_number": order_number, "sale_order_id": sale_order_id},
            )
            return False
        return True
