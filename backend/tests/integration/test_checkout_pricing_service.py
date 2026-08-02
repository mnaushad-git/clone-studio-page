"""CheckoutPricingService — the anti-tampering boundary between a client-submitted
cart and what a customer is actually charged. Every case here proves pricing comes
from catalogue_product_prices, never from the request.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.api.v1.schemas.checkout import CheckoutItemIn
from app.core.exceptions import NotFoundError, ValidationAppError
from app.services.checkout.pricing_service import CheckoutPricingService
from tests.integration.catalogue_factories import make_product_with_default_variant


def test_prices_from_catalogue_not_from_the_request(db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("10.00"))

    result = CheckoutPricingService(db_session).price_cart(
        [CheckoutItemIn(product_slug=product.slug, quantity=4)], promo_code=None
    )

    assert result.lines[0].unit_price == 10.00
    assert result.subtotal_amount == 40.00


def test_tax_is_vat_inclusive_not_added_on_top(db_session: Session) -> None:
    # D08/D21: prices already include VAT. At the default 5% rate, 105 inclusive of
    # VAT contains exactly 5 of VAT (105 / 1.05 = 100 net; 100 * 0.05 = 5).
    product = make_product_with_default_variant(db_session, amount=Decimal("105.00"))

    result = CheckoutPricingService(db_session).price_cart(
        [CheckoutItemIn(product_slug=product.slug, quantity=1)], promo_code=None
    )

    assert result.subtotal_amount == 105.00
    assert result.tax_amount == 5.00
    # total must equal subtotal + delivery, never subtotal + tax + delivery.
    assert result.total_amount == result.subtotal_amount + result.delivery_fee_amount


def test_valid_promo_code_applies_percentage_discount(db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))

    result = CheckoutPricingService(db_session).price_cart(
        [CheckoutItemIn(product_slug=product.slug, quantity=1)], promo_code="welcome10"
    )

    assert result.promo_code == "WELCOME10"
    assert result.discount_amount == 10.00


def test_unknown_promo_code_is_rejected_not_silently_ignored(db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"))

    with pytest.raises(ValidationAppError):
        CheckoutPricingService(db_session).price_cart(
            [CheckoutItemIn(product_slug=product.slug, quantity=1)], promo_code="NOT-A-CODE"
        )


def test_below_minimum_order_is_rejected(db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("5.00"))

    with pytest.raises(ValidationAppError):
        CheckoutPricingService(db_session).price_cart(
            [CheckoutItemIn(product_slug=product.slug, quantity=1)], promo_code=None
        )


def test_unknown_product_slug_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        CheckoutPricingService(db_session).price_cart(
            [CheckoutItemIn(product_slug="does-not-exist", quantity=1)], promo_code=None
        )


def test_inactive_product_raises_not_found(db_session: Session) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("100.00"), active=False)

    with pytest.raises(NotFoundError):
        CheckoutPricingService(db_session).price_cart(
            [CheckoutItemIn(product_slug=product.slug, quantity=1)], promo_code=None
        )


def test_empty_cart_is_rejected(db_session: Session) -> None:
    with pytest.raises(ValidationAppError):
        CheckoutPricingService(db_session).price_cart([], promo_code=None)


def test_multiple_lines_sum_correctly(db_session: Session) -> None:
    product_a = make_product_with_default_variant(db_session, amount=Decimal("20.00"))
    product_b = make_product_with_default_variant(db_session, amount=Decimal("15.00"))

    result = CheckoutPricingService(db_session).price_cart(
        [
            CheckoutItemIn(product_slug=product_a.slug, quantity=1),
            CheckoutItemIn(product_slug=product_b.slug, quantity=2),
        ],
        promo_code=None,
    )

    assert result.subtotal_amount == 50.00  # 20 + (15 * 2)
