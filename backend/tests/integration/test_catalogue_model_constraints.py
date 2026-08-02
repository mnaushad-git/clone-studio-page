"""Model-level constraint tests, run against real PostgreSQL (not SQLite) since these
verify actual DB-enforced UNIQUE/CHECK/FK/partial-index behaviour, not just ORM
attribute assignment. See docs/architecture/testing-strategy.md.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalogue.product_availability import CatalogueProductAvailability
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.models.catalogue.product_price import CatalogueProductPrice
from app.models.catalogue.product_recommendation import CatalogueProductRecommendation
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.storefront.section import StorefrontSection
from app.models.storefront.section_product import StorefrontSectionProduct
from tests.integration.catalogue_factories import make_category, make_product


def test_category_can_be_created(db_session: Session) -> None:
    category = make_category(db_session)
    assert category.id is not None
    assert category.active is True
    assert category.display_order == 0


def test_category_external_key_must_be_unique(db_session: Session) -> None:
    make_category(db_session, external_key="dup.category")
    with pytest.raises(IntegrityError):
        make_category(db_session, external_key="dup.category")
    db_session.rollback()


def test_product_sku_must_be_unique(db_session: Session) -> None:
    make_product(db_session, sku="TB-DUP-001")
    with pytest.raises(IntegrityError):
        make_product(db_session, sku="TB-DUP-001")
    db_session.rollback()


def test_product_slug_must_be_unique(db_session: Session) -> None:
    make_product(db_session, slug="dup-slug")
    with pytest.raises(IntegrityError):
        make_product(db_session, slug="dup-slug")
    db_session.rollback()


def test_product_requires_a_category(db_session: Session) -> None:
    with pytest.raises(IntegrityError):
        make_product(db_session, category_id=None)
    db_session.rollback()


def test_product_category_reference_must_exist(db_session: Session) -> None:
    with pytest.raises(IntegrityError):
        make_product(db_session, category_id=uuid.uuid4())
    db_session.rollback()


def test_product_cannot_recommend_itself(db_session: Session) -> None:
    product = make_product(db_session)
    with pytest.raises(IntegrityError):
        db_session.add(
            CatalogueProductRecommendation(
                product_id=product.id,
                recommended_product_id=product.id,
                recommendation_type="MANUAL",
            )
        )
        db_session.flush()
    db_session.rollback()


def test_only_one_merchandising_row_per_product(db_session: Session) -> None:
    product = make_product(db_session)
    db_session.add(CatalogueProductMerchandising(product_id=product.id))
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(CatalogueProductMerchandising(product_id=product.id))
        db_session.flush()
    db_session.rollback()


def test_duplicate_section_product_mapping_rejected(db_session: Session) -> None:
    section = StorefrontSection(
        external_key="test.section.dup",
        code="TEST_SECTION_DUP",
        title_en="Test Section",
    )
    db_session.add(section)
    db_session.flush()
    product = make_product(db_session)

    db_session.add(StorefrontSectionProduct(section_id=section.id, product_id=product.id))
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(StorefrontSectionProduct(section_id=section.id, product_id=product.id))
        db_session.flush()
    db_session.rollback()


def test_only_one_default_variant_per_product(db_session: Session) -> None:
    product = make_product(db_session)
    db_session.add(
        CatalogueProductVariant(
            product_id=product.id,
            external_key="test.variant.a",
            sku="TEST-VAR-A",
            name_en="Variant A",
            is_default=True,
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            CatalogueProductVariant(
                product_id=product.id,
                external_key="test.variant.b",
                sku="TEST-VAR-B",
                name_en="Variant B",
                is_default=True,
            )
        )
        db_session.flush()
    db_session.rollback()


def test_only_one_active_price_per_variant_and_currency(db_session: Session) -> None:
    product = make_product(db_session)
    variant = CatalogueProductVariant(
        product_id=product.id,
        external_key="test.variant.price",
        sku="TEST-VAR-PRICE",
        name_en="Priced Variant",
        is_default=True,
    )
    db_session.add(variant)
    db_session.flush()

    db_session.add(
        CatalogueProductPrice(product_variant_id=variant.id, currency="SAR", amount=10, active=True)
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            CatalogueProductPrice(
                product_variant_id=variant.id, currency="SAR", amount=20, active=True
            )
        )
        db_session.flush()
    db_session.rollback()


def test_price_amount_cannot_be_negative(db_session: Session) -> None:
    product = make_product(db_session)
    variant = CatalogueProductVariant(
        product_id=product.id,
        external_key="test.variant.negprice",
        sku="TEST-VAR-NEGPRICE",
        name_en="Variant",
        is_default=True,
    )
    db_session.add(variant)
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            CatalogueProductPrice(product_variant_id=variant.id, currency="SAR", amount=-1)
        )
        db_session.flush()
    db_session.rollback()


def test_price_includes_tax_defaults_to_null_and_is_preserved(db_session: Session) -> None:
    """The VAT-inclusive-vs-exclusive question is genuinely unresolved (D21) — the
    schema must never silently assume an answer.
    """
    product = make_product(db_session)
    variant = CatalogueProductVariant(
        product_id=product.id,
        external_key="test.variant.vat",
        sku="TEST-VAR-VAT",
        name_en="Variant",
        is_default=True,
    )
    db_session.add(variant)
    db_session.flush()
    price = CatalogueProductPrice(product_variant_id=variant.id, currency="SAR", amount=10)
    db_session.add(price)
    db_session.flush()
    assert price.price_includes_tax is None


def test_availability_status_must_be_a_known_value(db_session: Session) -> None:
    product = make_product(db_session)
    variant = CatalogueProductVariant(
        product_id=product.id,
        external_key="test.variant.avail",
        sku="TEST-VAR-AVAIL",
        name_en="Variant",
        is_default=True,
    )
    db_session.add(variant)
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            CatalogueProductAvailability(
                product_variant_id=variant.id, availability_status="NOT_A_REAL_STATUS"
            )
        )
        db_session.flush()
    db_session.rollback()


def test_category_cannot_be_its_own_parent(db_session: Session) -> None:
    category = make_category(db_session)
    with pytest.raises(IntegrityError):
        category.parent_id = category.id
        db_session.flush()
    db_session.rollback()
