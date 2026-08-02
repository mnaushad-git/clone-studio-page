"""Catalogue product merchandising — Admin-Portal-owned, never touched by Odoo sync.

Exactly one row per product (product_id unique). is_bestseller stays nullable: the
concept has no computed definition yet (per docs/catalogue/final-data-ownership.md),
so a missing value must never be inferred as false.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product import CatalogueProduct
    from app.models.catalogue.product_image import CatalogueProductImage


class CatalogueProductMerchandising(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_merchandising"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), unique=True, nullable=False
    )
    storefront_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_bestseller: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    badge_en: Mapped[str | None] = mapped_column(String(100))
    badge_ar: Mapped[str | None] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    marketing_title_en: Mapped[str | None] = mapped_column(String(255))
    marketing_title_ar: Mapped[str | None] = mapped_column(String(255))
    marketing_description_en: Mapped[str | None] = mapped_column(Text)
    marketing_description_ar: Mapped[str | None] = mapped_column(Text)
    seo_title_en: Mapped[str | None] = mapped_column(String(255))
    seo_title_ar: Mapped[str | None] = mapped_column(String(255))
    seo_description_en: Mapped[str | None] = mapped_column(Text)
    seo_description_ar: Mapped[str | None] = mapped_column(Text)
    storefront_image_override_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_images.id"), nullable=True
    )
    mobile_image_override_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_images.id"), nullable=True
    )

    product: Mapped[CatalogueProduct] = relationship(
        "CatalogueProduct", back_populates="merchandising"
    )
    storefront_image_override: Mapped[CatalogueProductImage | None] = relationship(
        "CatalogueProductImage", foreign_keys=[storefront_image_override_id]
    )
    mobile_image_override: Mapped[CatalogueProductImage | None] = relationship(
        "CatalogueProductImage", foreign_keys=[mobile_image_override_id]
    )
