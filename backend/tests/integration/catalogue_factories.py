"""Minimal-field factories for catalogue model/repository tests. Not a package under
app/ — test-only helpers, kept beside the tests that use them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.moment import CatalogueMoment
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_image import CatalogueProductImage
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.models.catalogue.product_moment import CatalogueProductMoment
from app.models.catalogue.product_price import CatalogueProductPrice
from app.models.catalogue.product_recipient import CatalogueProductRecipient
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.catalogue.recipient import CatalogueRecipient


def make_category(session: Session, **overrides: Any) -> CatalogueCategory:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "external_key": f"test.category.{suffix}",
        "code": f"C{suffix.upper()}",
        "slug": f"category-{suffix}",
        "name_en": f"Test Category {suffix}",
        "active": True,
        "display_order": 0,
    }
    defaults.update(overrides)
    category = CatalogueCategory(**defaults)
    session.add(category)
    session.flush()
    return category


def make_product(
    session: Session, category: CatalogueCategory | None = None, **overrides: Any
) -> CatalogueProduct:
    if category is None and "category_id" not in overrides:
        category = make_category(session)
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "external_key": f"test.product.{suffix}",
        "sku": f"TEST-{suffix.upper()}",
        "slug": f"product-{suffix}",
        "name_en": f"Test Product {suffix}",
        "product_type": "simple",
        "active": True,
        "sellable": True,
    }
    if category is not None:
        defaults["category_id"] = category.id
    defaults.update(overrides)
    product = CatalogueProduct(**defaults)
    session.add(product)
    session.flush()
    return product


def make_variant(
    session: Session, product: CatalogueProduct, **overrides: Any
) -> CatalogueProductVariant:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "product_id": product.id,
        "external_key": f"test.variant.{suffix}",
        "sku": f"{product.sku}-{suffix.upper()}",
        "name_en": f"{product.name_en} — {suffix}",
        "active": True,
        "is_default": False,
    }
    defaults.update(overrides)
    variant = CatalogueProductVariant(**defaults)
    session.add(variant)
    session.flush()
    return variant


def make_price(
    session: Session, variant: CatalogueProductVariant, **overrides: Any
) -> CatalogueProductPrice:
    defaults: dict[str, Any] = {
        "product_variant_id": variant.id,
        "currency": "SAR",
        "amount": Decimal("10.00"),
        "active": True,
        "price_includes_tax": None,
    }
    defaults.update(overrides)
    price = CatalogueProductPrice(**defaults)
    session.add(price)
    session.flush()
    return price


def make_product_with_default_variant(
    session: Session,
    category: CatalogueCategory | None = None,
    *,
    amount: Decimal = Decimal("10.00"),
    currency: str = "SAR",
    **overrides: Any,
) -> CatalogueProduct:
    """Convenience factory: a product plus its one default variant plus a current
    price row — the minimum shape CatalogueQueryService needs to build a
    ProductSummaryOut/ProductDetailOut without raising.
    """
    product = make_product(session, category=category, **overrides)
    variant = make_variant(session, product, is_default=True, sku=product.sku)
    make_price(session, variant, amount=amount, currency=currency)
    return product


def make_merchandising(
    session: Session, product: CatalogueProduct, **overrides: Any
) -> CatalogueProductMerchandising:
    defaults: dict[str, Any] = {
        "product_id": product.id,
        "storefront_visible": True,
        "featured": False,
        "is_new": False,
        "is_bestseller": None,
        "display_order": 0,
    }
    defaults.update(overrides)
    merch = CatalogueProductMerchandising(**defaults)
    session.add(merch)
    session.flush()
    return merch


def make_image(
    session: Session, product: CatalogueProduct, **overrides: Any
) -> CatalogueProductImage:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "product_id": product.id,
        "image_role": "PRIMARY",
        "original_path": f"src/assets/test-{suffix}.jpg",
        "display_order": 0,
        "active": True,
    }
    defaults.update(overrides)
    image = CatalogueProductImage(**defaults)
    session.add(image)
    session.flush()
    return image


def make_moment(session: Session, **overrides: Any) -> CatalogueMoment:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "external_key": f"test.moment.{suffix}",
        "code": f"M{suffix.upper()}",
        "slug": f"moment-{suffix}",
        "name_en": f"Test Moment {suffix}",
        "active": True,
        "display_order": 0,
    }
    defaults.update(overrides)
    moment = CatalogueMoment(**defaults)
    session.add(moment)
    session.flush()
    return moment


def make_recipient(session: Session, **overrides: Any) -> CatalogueRecipient:
    suffix = uuid.uuid4().hex[:8]
    defaults: dict[str, Any] = {
        "external_key": f"test.recipient.{suffix}",
        "code": f"R{suffix.upper()}",
        "slug": f"recipient-{suffix}",
        "name_en": f"Test Recipient {suffix}",
        "active": True,
        "display_order": 0,
    }
    defaults.update(overrides)
    recipient = CatalogueRecipient(**defaults)
    session.add(recipient)
    session.flush()
    return recipient


def link_moment(
    session: Session, product: CatalogueProduct, moment: CatalogueMoment, **overrides: Any
) -> CatalogueProductMoment:
    defaults: dict[str, Any] = {"product_id": product.id, "moment_id": moment.id, "active": True}
    defaults.update(overrides)
    link = CatalogueProductMoment(**defaults)
    session.add(link)
    session.flush()
    return link


def link_recipient(
    session: Session, product: CatalogueProduct, recipient: CatalogueRecipient, **overrides: Any
) -> CatalogueProductRecipient:
    defaults: dict[str, Any] = {
        "product_id": product.id,
        "recipient_id": recipient.id,
        "active": True,
    }
    defaults.update(overrides)
    link = CatalogueProductRecipient(**defaults)
    session.add(link)
    session.flush()
    return link
