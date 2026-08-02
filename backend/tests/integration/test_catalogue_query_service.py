from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.catalogue.catalogue_query_service import CatalogueQueryService
from tests.integration.catalogue_factories import (
    link_moment,
    link_recipient,
    make_category,
    make_image,
    make_merchandising,
    make_moment,
    make_price,
    make_product_with_default_variant,
    make_recipient,
    make_variant,
)


def test_list_categories_excludes_inactive(db_session: Session) -> None:
    active = make_category(db_session, active=True, name_en="Visible Category")
    make_category(db_session, active=False, name_en="Hidden Category")

    result = CatalogueQueryService(db_session).list_categories()

    slugs = {c.slug for c in result}
    assert active.slug in slugs
    assert "Hidden Category" not in {c.name_en for c in result}


def test_list_products_excludes_inactive_products(db_session: Session) -> None:
    category = make_category(db_session)
    active = make_product_with_default_variant(db_session, category=category, active=True)
    make_product_with_default_variant(db_session, category=category, active=False)

    result = CatalogueQueryService(db_session).list_products(limit=50)

    ids = {p.id for p in result.items}
    assert str(active.id) in ids
    assert len(result.items) == 1


def test_list_products_filters_by_category(db_session: Session) -> None:
    cat_a = make_category(db_session, slug="cat-a")
    cat_b = make_category(db_session, slug="cat-b")
    prod_a = make_product_with_default_variant(db_session, category=cat_a)
    make_product_with_default_variant(db_session, category=cat_b)

    result = CatalogueQueryService(db_session).list_products(category_slug="cat-a", limit=50)

    assert [p.id for p in result.items] == [str(prod_a.id)]


def test_list_products_filters_by_moment_and_recipient(db_session: Session) -> None:
    category = make_category(db_session)
    matching = make_product_with_default_variant(db_session, category=category)
    other = make_product_with_default_variant(db_session, category=category)
    moment = make_moment(db_session, slug="birthday")
    recipient = make_recipient(db_session, slug="for-her")
    link_moment(db_session, matching, moment)
    link_recipient(db_session, matching, recipient)

    by_moment = CatalogueQueryService(db_session).list_products(moment_slug="birthday", limit=50)
    by_recipient = CatalogueQueryService(db_session).list_products(
        recipient_slug="for-her", limit=50
    )

    assert [p.id for p in by_moment.items] == [str(matching.id)]
    assert [p.id for p in by_recipient.items] == [str(matching.id)]
    assert other.id != matching.id


def test_list_products_filters_by_merchandising_flags(db_session: Session) -> None:
    category = make_category(db_session)
    featured = make_product_with_default_variant(db_session, category=category)
    make_merchandising(db_session, featured, featured=True, is_bestseller=True, is_new=True)
    plain = make_product_with_default_variant(db_session, category=category)
    make_merchandising(db_session, plain, featured=False, is_bestseller=False, is_new=False)

    result = CatalogueQueryService(db_session).list_products(featured=True, limit=50)

    assert [p.id for p in result.items] == [str(featured.id)]


def test_list_products_search_matches_name(db_session: Session) -> None:
    category = make_category(db_session)
    make_product_with_default_variant(db_session, category=category, name_en="Chocolate Truffle")
    make_product_with_default_variant(db_session, category=category, name_en="Vanilla Sponge")

    result = CatalogueQueryService(db_session).list_products(search="choc", limit=50)

    assert [p.name_en for p in result.items] == ["Chocolate Truffle"]


def test_list_products_pagination_is_stable_and_totals_correct(db_session: Session) -> None:
    category = make_category(db_session)
    names = ["Alpha", "Bravo", "Charlie", "Delta"]
    for name in names:
        make_product_with_default_variant(db_session, category=category, name_en=name)

    service = CatalogueQueryService(db_session)
    page1 = service.list_products(category_slug=category.slug, limit=2, offset=0)
    page2 = service.list_products(category_slug=category.slug, limit=2, offset=2)

    assert page1.total == 4
    assert [p.name_en for p in page1.items] == ["Alpha", "Bravo"]
    assert [p.name_en for p in page2.items] == ["Charlie", "Delta"]
    assert {p.id for p in page1.items}.isdisjoint({p.id for p in page2.items})


def test_get_product_detail_returns_full_shape(db_session: Session) -> None:
    category = make_category(db_session)
    product = make_product_with_default_variant(
        db_session, category=category, amount=Decimal("25.50"), slug="detail-product"
    )
    make_merchandising(db_session, product, badge_en="New")
    make_image(db_session, product, image_role="PRIMARY", display_order=0)
    make_image(db_session, product, image_role="GALLERY", display_order=1)
    moment = make_moment(db_session, name_en="Birthday")
    recipient = make_recipient(db_session, name_en="For Her")
    link_moment(db_session, product, moment)
    link_recipient(db_session, product, recipient)

    detail = CatalogueQueryService(db_session).get_product_detail("detail-product")

    assert detail is not None
    assert detail.price == "25.50"
    assert detail.primary_image is not None
    assert len(detail.gallery_images) == 1
    assert [m.name_en for m in detail.moments] == ["Birthday"]
    assert [r.name_en for r in detail.recipients] == ["For Her"]
    assert detail.merchandising.badge_en == "New"


def test_get_product_detail_returns_none_for_missing_or_inactive(db_session: Session) -> None:
    service = CatalogueQueryService(db_session)
    assert service.get_product_detail("does-not-exist") is None

    category = make_category(db_session)
    make_product_with_default_variant(
        db_session, category=category, slug="inactive-product", active=False
    )
    assert service.get_product_detail("inactive-product") is None


def test_get_product_detail_includes_non_default_variant_with_own_price(
    db_session: Session,
) -> None:
    category = make_category(db_session)
    product = make_product_with_default_variant(
        db_session, category=category, slug="multi-variant", product_type="variant_parent"
    )
    extra_variant = make_variant(db_session, product, is_default=False, name_en="9 inch")
    make_price(db_session, extra_variant, amount=Decimal("40.00"))

    detail = CatalogueQueryService(db_session).get_product_detail("multi-variant")

    assert detail is not None
    assert len(detail.variants) == 2
    non_default = [v for v in detail.variants if not v.is_default][0]
    assert non_default.price == "40.00"


def test_get_homepage_sections_match_current_storefront_rules(db_session: Session) -> None:
    cupcakes = make_category(db_session, slug="cupcakes")
    gifts = make_category(db_session, slug="gifts")
    donuts = make_category(db_session, slug="donuts")
    chocolates = make_category(db_session, slug="chocolates")
    extras = make_category(db_session, slug="extras")

    for i in range(5):
        p = make_product_with_default_variant(
            db_session, category=cupcakes, name_en=f"Cupcake {i}", slug=f"cupcake-{i}"
        )
        make_merchandising(db_session, p, display_order=i)

    gift_product = make_product_with_default_variant(db_session, category=gifts, slug="gift-1")
    make_merchandising(db_session, gift_product, display_order=100)

    cream_donut = make_product_with_default_variant(
        db_session, category=donuts, slug="cream-cheese-donut"
    )
    make_merchandising(db_session, cream_donut, display_order=101)

    sprinkle = make_product_with_default_variant(db_session, category=cupcakes, slug="sprinkle-1")
    make_merchandising(db_session, sprinkle, display_order=102)

    choc = make_product_with_default_variant(db_session, category=chocolates, slug="choc-1")
    make_merchandising(db_session, choc, display_order=103)

    extra = make_product_with_default_variant(db_session, category=extras, slug="extra-1")
    make_merchandising(db_session, extra, display_order=104)

    new_product = make_product_with_default_variant(db_session, category=cupcakes, slug="new-1")
    make_merchandising(db_session, new_product, is_new=True, display_order=105)

    homepage = CatalogueQueryService(db_session).get_homepage()

    assert len(homepage.hero) == 4  # capped at 4, matches products.ts's .slice(0, 4)
    assert all(p.category.slug == "cupcakes" for p in homepage.hero)

    gifts_slugs = {p.slug for p in homepage.gifts}
    assert "gift-1" in gifts_slugs
    assert "cream-cheese-donut" in gifts_slugs

    assert {p.slug for p in homepage.divine} == {"sprinkle-1"}
    assert {p.slug for p in homepage.chocolates} == {"choc-1"}
    assert {p.slug for p in homepage.extras} == {"extra-1"}
    assert {p.slug for p in homepage.new} == {"new-1"}
