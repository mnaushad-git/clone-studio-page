"""Server-authoritative checkout pricing.

Every price here comes from catalogue_product_prices (never a client-submitted unit
price) — this is the anti-tampering boundary between the Storefront's cart (client-side,
localStorage) and a real order. A client can send any productId/qty/promo it wants; the
totals a customer is actually charged always come from this module.

Prices are VAT-inclusive (matches the Storefront's D08/D21 convention, see
src/lib/store.ts): tax reported here is the VAT portion already folded into the
subtotal, never added on top of it.

Promo codes and delivery pricing are Admin-Portal-managed (promo_codes,
delivery_settings/delivery_slots — task brief §11/§12), not env config or a hardcoded
dict: an admin edit takes effect on the very next checkout, no redeploy.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.v1.schemas.checkout import CheckoutItemIn
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.admin.promo_code import PromoCode
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.repositories.admin.delivery_repository import (
    DeliverySettingsRepository,
    DeliverySlotRepository,
)
from app.repositories.admin.promo_code_repository import PromoCodeRepository
from app.repositories.catalogue.product_repository import ProductRepository

DEFAULT_CURRENCY = "SAR"


@dataclass(frozen=True)
class PricedLine:
    product: CatalogueProduct
    variant: CatalogueProductVariant
    quantity: int
    unit_price: float
    line_total: float
    inscription: str | None


@dataclass(frozen=True)
class PricingResult:
    lines: list[PricedLine] = field(default_factory=list)
    currency: str = DEFAULT_CURRENCY
    subtotal_amount: float = 0.0
    discount_amount: float = 0.0
    promo_code: str | None = None
    promo_code_id: uuid.UUID | None = None
    discount_type: str | None = None
    discount_value: float | None = None
    tax_amount: float = 0.0
    delivery_fee_amount: float = 0.0
    total_amount: float = 0.0


def _round(amount: float) -> float:
    return round(amount + 1e-9, 2)


def _current_price(variant: CatalogueProductVariant, currency: str) -> float | None:
    for price in variant.prices:
        if price.active and price.currency == currency:
            return float(price.amount)
    return None


def _select_variant(
    product: CatalogueProduct, selected_attributes: dict[str, str]
) -> CatalogueProductVariant:
    """Resolves the cart line's selected combination (an arbitrary number of named
    axes — code -> selected value_label_en, e.g. {"size": "9 INCH", "flavor":
    "Chocolate"}, sourced from `catalogue_product_attribute_values`, the single source
    of truth for a variant's per-axis data — see
    docs/integrations/odoo-catalogue-variant-model.md) to its priced/SKU'd variant.

    Each provided (code, value) pair must match that variant's own value for that
    code — a variant lacking one of the provided codes entirely never matches (the
    client only ever sends codes it saw on this product's own `VariantOut.attributes`,
    so there is no "customer sends a preference for an axis this product doesn't have"
    case to special-case around, unlike the old two-hardcoded-slot version this
    replaces).
    """
    active_variants = [v for v in product.variants if v.active]
    if selected_attributes:
        for variant in active_variants:
            attrs = {a.attribute_code: a.value_label_en for a in variant.attribute_values}
            if any(attrs.get(code) != value for code, value in selected_attributes.items()):
                continue
            return variant
    for variant in active_variants:
        if variant.is_default:
            return variant
    if not active_variants:
        raise NotFoundError(f"Product {product.slug!r} has no active variant to price.")
    return active_variants[0]


class CheckoutPricingService:
    """Prices a cart against the live catalogue. Stateless — never persists anything;
    OrderService is what turns a PricingResult into a stored Order."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.promo_codes = PromoCodeRepository(session)
        self.delivery_settings = DeliverySettingsRepository(session)
        self.delivery_slots = DeliverySlotRepository(session)
        self.settings = get_settings()

    def _resolve_promo(self, promo_code: str, subtotal: float) -> tuple[PromoCode, float]:
        normalized = promo_code.strip().upper()
        promo = self.promo_codes.get_by_code(normalized)
        if promo is None or not promo.is_active:
            raise ValidationAppError(f"Promo code {promo_code!r} is not valid.")

        now = datetime.now(UTC)
        if promo.valid_from is not None and promo.valid_from > now:
            raise ValidationAppError(f"Promo code {promo_code!r} is not active yet.")
        if promo.valid_until is not None and promo.valid_until < now:
            raise ValidationAppError(f"Promo code {promo_code!r} has expired.")
        if promo.usage_limit is not None and promo.usage_count >= promo.usage_limit:
            raise ValidationAppError(f"Promo code {promo_code!r} has reached its usage limit.")
        if subtotal < float(promo.minimum_order_amount):
            raise ValidationAppError(
                f"Promo code {promo_code!r} requires a minimum order of "
                f"{float(promo.minimum_order_amount):.2f}."
            )

        if promo.discount_type == "PERCENTAGE":
            discount = _round(subtotal * (float(promo.discount_value) / 100))
        else:
            discount = _round(float(promo.discount_value))
        if promo.maximum_discount_amount is not None:
            discount = min(discount, float(promo.maximum_discount_amount))
        discount = min(discount, subtotal)

        return promo, discount

    def validate_delivery_slot(self, delivery_time: str | None) -> None:
        """MVP-scoped slot validation (Admin Portal MVP plan, decision 6): checks the
        submitted delivery_time against currently active slot labels. Does not cross-
        check the calendar date against delivery_settings.available_days — the
        Storefront sends a free-text date label ("Tomorrow", a picked calendar date),
        not a parseable ISO date, so day-of-week availability isn't enforced yet."""
        if not delivery_time:
            return
        active_labels = {slot.label for slot in self.delivery_slots.list_active()}
        if active_labels and delivery_time not in active_labels:
            raise ValidationAppError(f"Delivery time {delivery_time!r} is not currently available.")

    def price_cart(
        self, items: list[CheckoutItemIn], promo_code: str | None, currency: str = DEFAULT_CURRENCY
    ) -> PricingResult:
        if not items:
            raise ValidationAppError("Cart is empty.")

        lines: list[PricedLine] = []
        for item in items:
            product = self.products.get_by_slug_with_catalogue_data(item.product_slug)
            if product is None or not product.active or not product.sellable:
                raise NotFoundError(f"Product {item.product_slug!r} is not available.")

            variant = _select_variant(product, item.attributes)
            unit_price = _current_price(variant, currency)
            if unit_price is None:
                raise NotFoundError(
                    f"Product {item.product_slug!r} has no active {currency} price."
                )

            line_total = _round(unit_price * item.quantity)
            lines.append(
                PricedLine(
                    product=product,
                    variant=variant,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    inscription=item.inscription,
                )
            )

        subtotal = _round(sum(line.line_total for line in lines))

        resolved_promo: PromoCode | None = None
        discount = 0.0
        if promo_code:
            resolved_promo, discount = self._resolve_promo(promo_code, subtotal)

        delivery = self.delivery_settings.get_singleton()
        if not delivery.delivery_enabled:
            raise ValidationAppError("Delivery is currently unavailable.")

        net = max(0.0, subtotal - discount)
        min_order = float(delivery.minimum_order_amount)
        if net < min_order:
            raise ValidationAppError(f"Minimum order is {min_order:.2f} {currency}.")

        rate = self.settings.checkout_tax_rate_percent / 100
        tax = _round((net * rate) / (1 + rate))

        threshold = float(delivery.free_delivery_threshold)
        delivery_fee = (
            0.0 if threshold > 0 and net >= threshold else float(delivery.flat_delivery_fee)
        )
        delivery_fee = _round(delivery_fee)

        total = _round(net + delivery_fee)

        return PricingResult(
            lines=lines,
            currency=currency,
            subtotal_amount=subtotal,
            discount_amount=discount,
            promo_code=resolved_promo.code if resolved_promo else None,
            promo_code_id=resolved_promo.id if resolved_promo else None,
            discount_type=resolved_promo.discount_type if resolved_promo else None,
            discount_value=(float(resolved_promo.discount_value) if resolved_promo else None),
            tax_amount=tax,
            delivery_fee_amount=delivery_fee,
            total_amount=total,
        )
