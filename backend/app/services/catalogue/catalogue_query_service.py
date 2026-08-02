"""Read-only catalogue query service — backs every /api/v1/catalogue/* endpoint.

Route handlers stay thin (rule 6): they call one method here and return its Pydantic
result directly. PostgreSQL (never Odoo, never the browser) is the serving source for
every read here (CLAUDE.md rule 2) — this module only talks to repositories, never to
app.integrations.odoo.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.schemas.catalogue import (
    CategoryOut,
    HomepageOut,
    ImageOut,
    MerchandisingOut,
    MomentOut,
    PaginatedProductsOut,
    ProductDetailOut,
    ProductSummaryOut,
    RecipientOut,
    VariantAttributeOut,
    VariantOut,
)
from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.moment import CatalogueMoment
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_image import CatalogueProductImage
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.catalogue.recipient import CatalogueRecipient
from app.repositories.catalogue.category_repository import CategoryRepository
from app.repositories.catalogue.moment_repository import MomentRepository
from app.repositories.catalogue.product_moment_repository import ProductMomentRepository
from app.repositories.catalogue.product_recipient_repository import ProductRecipientRepository
from app.repositories.catalogue.product_repository import ProductRepository
from app.repositories.catalogue.recipient_repository import RecipientRepository

DEFAULT_CURRENCY = "SAR"

# Homepage section rules — ported 1:1 from the current Storefront's src/lib/products.ts
# `featured` object (rule 20: preserve existing visual behaviour exactly). The frontend
# no longer computes these slices itself; this endpoint is the single source of truth.
_DIVINE_SLUG_PREFIX = "sprinkle-"
_GIFTS_EXTRA_SLUG = "cream-cheese-donut"


class CatalogueQueryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.categories = CategoryRepository(session)
        self.products = ProductRepository(session)
        self.moments = MomentRepository(session)
        self.recipients = RecipientRepository(session)
        self.product_moments = ProductMomentRepository(session)
        self.product_recipients = ProductRecipientRepository(session)

    # -- categories / moments / recipients --------------------------------------------

    def list_categories(self) -> list[CategoryOut]:
        return [_category_out(c) for c in self.categories.list_active()]

    def list_moments(self) -> list[MomentOut]:
        return [_moment_out(m) for m in self.moments.list_active()]

    def list_recipients(self) -> list[RecipientOut]:
        return [_recipient_out(r) for r in self.recipients.list_active()]

    # -- products -----------------------------------------------------------------

    def list_products(
        self,
        *,
        category_slug: str | None = None,
        moment_slug: str | None = None,
        recipient_slug: str | None = None,
        featured: bool | None = None,
        is_bestseller: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedProductsOut:
        items, total = self.products.search(
            category_slug=category_slug,
            moment_slug=moment_slug,
            recipient_slug=recipient_slug,
            featured=featured,
            is_bestseller=is_bestseller,
            is_new=is_new,
            search=search,
            limit=limit,
            offset=offset,
        )
        moments_by_product, recipients_by_product = self._moments_recipients_for(items)
        return PaginatedProductsOut(
            items=[
                _summary_out(
                    p, moments_by_product.get(p.id, []), recipients_by_product.get(p.id, [])
                )
                for p in items
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def _moments_recipients_for(
        self, products: Sequence[CatalogueProduct]
    ) -> tuple[dict[uuid.UUID, list[MomentOut]], dict[uuid.UUID, list[RecipientOut]]]:
        """Batch-loads moment/recipient links for a page of products in 2 queries
        total (not one per product) and maps them to already-hydrated MomentOut/
        RecipientOut DTOs, keyed by product_id."""
        product_ids = [p.id for p in products]
        moment_links = self.product_moments.list_for_products(product_ids)
        recipient_links = self.product_recipients.list_for_products(product_ids)

        moments_by_id = {m.id: _moment_out(m) for m in self.moments.list_active()}
        recipients_by_id = {r.id: _recipient_out(r) for r in self.recipients.list_active()}

        moments_by_product: dict[uuid.UUID, list[MomentOut]] = {}
        for link in moment_links:
            if link.active and link.moment_id in moments_by_id:
                moments_by_product.setdefault(link.product_id, []).append(
                    moments_by_id[link.moment_id]
                )

        recipients_by_product: dict[uuid.UUID, list[RecipientOut]] = {}
        for rlink in recipient_links:
            if rlink.active and rlink.recipient_id in recipients_by_id:
                recipients_by_product.setdefault(rlink.product_id, []).append(
                    recipients_by_id[rlink.recipient_id]
                )

        return moments_by_product, recipients_by_product

    def get_product_detail(self, slug: str) -> ProductDetailOut | None:
        product = self.products.get_by_slug_with_catalogue_data(slug)
        if product is None or not product.active:
            return None

        moments_by_product, recipients_by_product = self._moments_recipients_for([product])
        moments = moments_by_product.get(product.id, [])
        recipients = recipients_by_product.get(product.id, [])

        variant = _default_variant(product)
        price = _current_price(variant)

        return ProductDetailOut(
            id=str(product.id),
            external_key=product.external_key,
            sku=product.sku,
            slug=product.slug,
            name_en=product.name_en,
            name_ar=product.name_ar,
            description_en=product.description_en,
            description_ar=product.description_ar,
            category=_category_out(product.category),
            price=_format_price(price),
            currency=price.currency if price else DEFAULT_CURRENCY,
            price_includes_tax=price.price_includes_tax if price else None,
            primary_image=_image_out(_primary_image(product)),
            gallery_images=[_image_out(i) for i in _gallery_images(product)],
            variants=[
                _variant_out(v)
                for v in sorted(product.variants, key=lambda v: v.sku)
                if v.active
            ],
            merchandising=_merchandising_out(product.merchandising),
            moments=moments,
            recipients=recipients,
            availability_status=_availability_status(variant),
        )

    # -- homepage -----------------------------------------------------------------

    def get_homepage(self) -> HomepageOut:
        all_products = self.products.list_active_with_catalogue_data()

        def by_category(slug: str) -> list[CatalogueProduct]:
            return [p for p in all_products if p.category.slug == slug]

        hero = by_category("cupcakes")[:4]
        gifts = [
            p for p in all_products if p.category.slug == "gifts" or p.slug == _GIFTS_EXTRA_SLUG
        ][:4]
        divine = [p for p in all_products if p.slug.startswith(_DIVINE_SLUG_PREFIX)]
        chocolates = by_category("chocolates")
        extras = by_category("extras")
        new = [p for p in all_products if p.merchandising is not None and p.merchandising.is_new]

        moments_by_product, recipients_by_product = self._moments_recipients_for(all_products)

        def summaries(items: list[CatalogueProduct]) -> list[ProductSummaryOut]:
            return [
                _summary_out(
                    p, moments_by_product.get(p.id, []), recipients_by_product.get(p.id, [])
                )
                for p in items
            ]

        return HomepageOut(
            hero=summaries(hero),
            gifts=summaries(gifts),
            divine=summaries(divine),
            chocolates=summaries(chocolates),
            extras=summaries(extras),
            new=summaries(new),
        )


# -- product -> DTO assembly helpers (module-level, no session access needed) --------


def _default_variant(product: CatalogueProduct) -> CatalogueProductVariant:
    for variant in product.variants:
        if variant.is_default and variant.active:
            return variant
    # Every product has at least one variant (seed invariant); this is an assertion
    # of that invariant, not a real fallback path.
    return product.variants[0]


def _current_price(variant: CatalogueProductVariant, currency: str = DEFAULT_CURRENCY) -> Any:
    for price in variant.prices:
        if price.active and price.currency == currency:
            return price
    return None


def _format_price(price: Any) -> str:
    if price is None:
        return "0.00"
    return f"{float(price.amount):.2f}"


def _primary_image(product: CatalogueProduct) -> CatalogueProductImage | None:
    for image in product.images:
        if image.image_role == "PRIMARY" and image.active:
            return image
    return None


def _gallery_images(product: CatalogueProduct) -> list[CatalogueProductImage]:
    return sorted(
        (i for i in product.images if i.image_role == "GALLERY" and i.active),
        key=lambda i: i.display_order,
    )


def _availability_status(variant: CatalogueProductVariant) -> str:
    if variant.availability is None:
        return "UNKNOWN"
    return variant.availability.availability_status


def _image_out(image: CatalogueProductImage | None) -> ImageOut | None:
    if image is None:
        return None
    return ImageOut(
        url=image.storage_url or image.original_path,
        role=image.image_role,
        alt_text_en=image.alt_text_en,
        alt_text_ar=image.alt_text_ar,
        display_order=image.display_order,
    )


def _variant_out(variant: CatalogueProductVariant) -> VariantOut:
    price = _current_price(variant)
    return VariantOut(
        id=str(variant.id),
        external_key=variant.external_key,
        sku=variant.sku,
        name_en=variant.name_en,
        is_default=variant.is_default,
        attributes=[
            VariantAttributeOut(
                code=a.attribute_code,
                name_en=a.attribute_name_en,
                value_label_en=a.value_label_en,
            )
            # created_at order matches the source JSON's/Odoo's own axis order (e.g.
            # size before flavor for buttercream-cake) — no separate display_order
            # column needed.
            for a in sorted(variant.attribute_values, key=lambda a: a.created_at)
        ],
        price=_format_price(price) if price else None,
        currency=price.currency if price else None,
    )


def _merchandising_out(merch: CatalogueProductMerchandising | None) -> MerchandisingOut:
    if merch is None:
        return MerchandisingOut(
            featured=False, is_new=False, is_bestseller=None, badge_en=None, badge_ar=None
        )
    return MerchandisingOut(
        featured=merch.featured,
        is_new=merch.is_new,
        is_bestseller=merch.is_bestseller,
        badge_en=merch.badge_en,
        badge_ar=merch.badge_ar,
    )


def _category_out(category: CatalogueCategory) -> CategoryOut:
    return CategoryOut(
        id=str(category.id),
        external_key=category.external_key,
        code=category.code,
        slug=category.slug,
        name_en=category.name_en,
        name_ar=category.name_ar,
        description_en=category.description_en,
        description_ar=category.description_ar,
        display_order=category.display_order,
    )


def _moment_out(moment: CatalogueMoment) -> MomentOut:
    return MomentOut(
        id=str(moment.id),
        external_key=moment.external_key,
        slug=moment.slug,
        name_en=moment.name_en,
        name_ar=moment.name_ar,
        description_en=moment.description_en,
        description_ar=moment.description_ar,
        display_order=moment.display_order,
    )


def _recipient_out(recipient: CatalogueRecipient) -> RecipientOut:
    return RecipientOut(
        id=str(recipient.id),
        external_key=recipient.external_key,
        slug=recipient.slug,
        name_en=recipient.name_en,
        name_ar=recipient.name_ar,
        description_en=recipient.description_en,
        description_ar=recipient.description_ar,
        display_order=recipient.display_order,
    )


def _summary_out(
    product: CatalogueProduct, moments: list[MomentOut], recipients: list[RecipientOut]
) -> ProductSummaryOut:
    variant = _default_variant(product)
    price = _current_price(variant)
    return ProductSummaryOut(
        id=str(product.id),
        external_key=product.external_key,
        sku=product.sku,
        slug=product.slug,
        name_en=product.name_en,
        name_ar=product.name_ar,
        short_description_en=product.short_description_en,
        category=_category_out(product.category),
        price=_format_price(price),
        currency=price.currency if price else DEFAULT_CURRENCY,
        price_includes_tax=price.price_includes_tax if price else None,
        primary_image=_image_out(_primary_image(product)),
        merchandising=_merchandising_out(product.merchandising),
        moments=moments,
        recipients=recipients,
        availability_status=_availability_status(variant),
    )
