from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.moment import CatalogueMoment
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.models.catalogue.product_moment import CatalogueProductMoment
from app.models.catalogue.product_recipient import CatalogueProductRecipient
from app.models.catalogue.product_variant import CatalogueProductVariant
from app.models.catalogue.recipient import CatalogueRecipient
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
    SkuRepositoryMixin,
    SlugRepositoryMixin,
)

# Shared eager-load plan for every catalogue-API read path: category, merchandising,
# images, and variants (with their prices/availability) are always needed to build a
# ProductSummaryOut/ProductDetailOut, so loading them here avoids an N+1 query storm
# instead of lazy-loading per product in the service layer.
_CATALOGUE_LOAD_OPTIONS = (
    selectinload(CatalogueProduct.category),
    selectinload(CatalogueProduct.merchandising),
    selectinload(CatalogueProduct.images),
    selectinload(CatalogueProduct.variants).selectinload(CatalogueProductVariant.prices),
    selectinload(CatalogueProduct.variants).selectinload(CatalogueProductVariant.availability),
    # Needed by catalogue_query_service._variant_out() (storefront display) and
    # pricing_service._select_variant() (checkout matching) — both read a variant's
    # per-axis data from this relationship, the single source of truth for it.
    selectinload(CatalogueProduct.variants).selectinload(CatalogueProductVariant.attribute_values),
)


class ProductRepository(
    ExternalKeyRepositoryMixin[CatalogueProduct],
    SkuRepositoryMixin[CatalogueProduct],
    SlugRepositoryMixin[CatalogueProduct],
    ActiveListRepositoryMixin[CatalogueProduct],
    BaseRepository[CatalogueProduct],
):
    model = CatalogueProduct
    order_by: ClassVar[tuple] = (CatalogueProduct.name_en,)

    def get_by_slug_with_catalogue_data(self, slug: str) -> CatalogueProduct | None:
        stmt = select(self.model).where(self.model.slug == slug).options(*_CATALOGUE_LOAD_OPTIONS)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_odoo_product_template_id(self, odoo_template_id: int) -> CatalogueProduct | None:
        stmt = select(self.model).where(self.model.odoo_product_template_id == odoo_template_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_active_with_catalogue_data(self) -> Sequence[CatalogueProduct]:
        """All active products, eager-loaded, sorted by merchandising.display_order —
        the ordering the current Storefront homepage relies on (matches the original
        products.ts array order 1:1, per product-merchandising.json's display_order).
        """
        stmt = (
            select(self.model)
            .join(
                CatalogueProductMerchandising,
                CatalogueProductMerchandising.product_id == self.model.id,
            )
            .where(self.model.active.is_(True))
            .options(*_CATALOGUE_LOAD_OPTIONS)
            .order_by(CatalogueProductMerchandising.display_order, self.model.id)
        )
        return self.session.execute(stmt).unique().scalars().all()

    def _base_filtered_query(
        self,
        *,
        category_slug: str | None,
        moment_slug: str | None,
        recipient_slug: str | None,
        featured: bool | None,
        is_bestseller: bool | None,
        is_new: bool | None,
        search: str | None,
    ) -> Select[tuple[CatalogueProduct]]:
        stmt = select(self.model).where(self.model.active.is_(True))

        if category_slug:
            stmt = stmt.join(
                CatalogueCategory, self.model.category_id == CatalogueCategory.id
            ).where(CatalogueCategory.slug == category_slug)

        if moment_slug:
            stmt = (
                stmt.join(
                    CatalogueProductMoment, CatalogueProductMoment.product_id == self.model.id
                )
                .join(CatalogueMoment, CatalogueMoment.id == CatalogueProductMoment.moment_id)
                .where(CatalogueMoment.slug == moment_slug, CatalogueProductMoment.active.is_(True))
            )

        if recipient_slug:
            stmt = (
                stmt.join(
                    CatalogueProductRecipient, CatalogueProductRecipient.product_id == self.model.id
                )
                .join(
                    CatalogueRecipient,
                    CatalogueRecipient.id == CatalogueProductRecipient.recipient_id,
                )
                .where(
                    CatalogueRecipient.slug == recipient_slug,
                    CatalogueProductRecipient.active.is_(True),
                )
            )

        if featured is not None or is_bestseller is not None or is_new is not None:
            stmt = stmt.join(
                CatalogueProductMerchandising,
                CatalogueProductMerchandising.product_id == self.model.id,
            )
            if featured is not None:
                stmt = stmt.where(CatalogueProductMerchandising.featured.is_(featured))
            if is_bestseller is not None:
                stmt = stmt.where(CatalogueProductMerchandising.is_bestseller.is_(is_bestseller))
            if is_new is not None:
                stmt = stmt.where(CatalogueProductMerchandising.is_new.is_(is_new))

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    self.model.name_en.ilike(pattern),
                    self.model.description_en.ilike(pattern),
                )
            )

        return stmt

    def search(
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
    ) -> tuple[Sequence[CatalogueProduct], int]:
        """Active-only, filtered, paginated product search. Returns (page, total_count)
        — stable sort by name_en then id so pagination never reorders rows between pages.
        """
        base = self._base_filtered_query(
            category_slug=category_slug,
            moment_slug=moment_slug,
            recipient_slug=recipient_slug,
            featured=featured,
            is_bestseller=is_bestseller,
            is_new=is_new,
            search=search,
        )

        total = self.session.execute(
            select(func.count()).select_from(base.with_only_columns(self.model.id).subquery())
        ).scalar_one()

        page_stmt = (
            base.options(*_CATALOGUE_LOAD_OPTIONS)
            .order_by(self.model.name_en, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        items = self.session.execute(page_stmt).scalars().all()
        return items, total

    def search_admin(
        self,
        *,
        category_slug: str | None = None,
        active: bool | None = None,
        featured: bool | None = None,
        is_bestseller: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[CatalogueProduct], int]:
        """Admin product list (task brief §10) — unlike search() above, this
        deliberately does NOT force active=True: staff need to see disabled products
        too, with Active as just another filterable column. Also searches SKU, which
        the public catalogue search does not expose."""
        stmt = select(self.model)

        if category_slug:
            stmt = stmt.join(
                CatalogueCategory, self.model.category_id == CatalogueCategory.id
            ).where(CatalogueCategory.slug == category_slug)

        if active is not None:
            stmt = stmt.where(self.model.active.is_(active))

        if featured is not None or is_bestseller is not None or is_new is not None:
            stmt = stmt.join(
                CatalogueProductMerchandising,
                CatalogueProductMerchandising.product_id == self.model.id,
            )
            if featured is not None:
                stmt = stmt.where(CatalogueProductMerchandising.featured.is_(featured))
            if is_bestseller is not None:
                stmt = stmt.where(CatalogueProductMerchandising.is_bestseller.is_(is_bestseller))
            if is_new is not None:
                stmt = stmt.where(CatalogueProductMerchandising.is_new.is_(is_new))

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(self.model.name_en.ilike(pattern), self.model.sku.ilike(pattern)))

        total = self.session.execute(
            select(func.count()).select_from(stmt.with_only_columns(self.model.id).subquery())
        ).scalar_one()

        page_stmt = (
            stmt.options(*_CATALOGUE_LOAD_OPTIONS)
            .order_by(self.model.name_en, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        items = self.session.execute(page_stmt).unique().scalars().all()
        return items, total
