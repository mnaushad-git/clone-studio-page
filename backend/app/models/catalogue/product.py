"""Catalogue product — Odoo-owned commercial identity.

Never stores sales price directly (prices live in catalogue_product_prices, keyed off
the variant, since every product has at least one default variant). Merchandising
(storefront visibility, badges, marketing copy) lives in a separate
catalogue_product_merchandising table, never here — see
docs/architecture/data-ownership.md §4.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import SourceSyncMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.category import CatalogueCategory
    from app.models.catalogue.product_image import CatalogueProductImage
    from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
    from app.models.catalogue.product_variant import CatalogueProductVariant

# Values a product's product_type may take. variant_parent is reserved for products with
# a genuine per-product variant model (only buttercream-cake today, per D11) — every other
# product is "simple" with exactly one default variant.
PRODUCT_TYPES = ("simple", "variant_parent")

# Provenance of the current row's data — where "seed" is the Phase 2A/3 canonical JSON
# import and "odoo"/"admin" are future sync/edit sources.
SOURCE_SYSTEMS = ("seed", "odoo", "admin")


class CatalogueProduct(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_products"
    __table_args__ = (
        CheckConstraint(
            f"product_type IN {PRODUCT_TYPES}", name="ck_catalogue_products_product_type"
        ),
        CheckConstraint(
            f"source_system IN {SOURCE_SYSTEMS}", name="ck_catalogue_products_source_system"
        ),
        Index("ix_catalogue_products_category_id", "category_id"),
        Index("ix_catalogue_products_active", "active"),
        Index("ix_catalogue_products_sellable", "sellable"),
        Index("ix_catalogue_products_odoo_product_template_id", "odoo_product_template_id"),
        Index("ix_catalogue_products_name_en", "name_en"),
    )

    external_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_ar: Mapped[str | None] = mapped_column(Text)
    short_description_en: Mapped[str | None] = mapped_column(String(500))
    short_description_ar: Mapped[str | None] = mapped_column(String(500))
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_categories.id"), nullable=False
    )
    product_type: Mapped[str] = mapped_column(String(20), nullable=False, default="simple")
    unit_of_measure: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    sellable: Mapped[bool] = mapped_column(nullable=False, default=True)
    odoo_product_template_id: Mapped[int | None] = mapped_column(Integer)

    category: Mapped[CatalogueCategory] = relationship(
        "CatalogueCategory", back_populates="products"
    )
    variants: Mapped[list[CatalogueProductVariant]] = relationship(
        "CatalogueProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list[CatalogueProductImage]] = relationship(
        "CatalogueProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        foreign_keys="CatalogueProductImage.product_id",
    )
    merchandising: Mapped[CatalogueProductMerchandising | None] = relationship(
        "CatalogueProductMerchandising", back_populates="product", cascade="all, delete-orphan"
    )
