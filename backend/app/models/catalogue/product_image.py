"""Catalogue product image.

storage_url stays null until media migration to object storage happens; original_path
preserves the current repo-relative source path as provenance either way.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import SourceSyncMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product import CatalogueProduct
    from app.models.catalogue.product_variant import CatalogueProductVariant

IMAGE_ROLES = ("PRIMARY", "GALLERY", "STOREFRONT_OVERRIDE", "MOBILE_OVERRIDE")


class CatalogueProductImage(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_images"
    __table_args__ = (
        CheckConstraint(f"image_role IN {IMAGE_ROLES}", name="ck_catalogue_product_images_role"),
        CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_images_display_order_nonneg"
        ),
        Index("ix_catalogue_product_images_product_id", "product_id"),
        Index("ix_catalogue_product_images_variant_id", "product_variant_id"),
        Index("ix_catalogue_product_images_odoo_image_id", "odoo_image_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), nullable=False
    )
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_variants.id"), nullable=True
    )
    image_role: Mapped[str] = mapped_column(String(30), nullable=False, default="GALLERY")
    original_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_url: Mapped[str | None] = mapped_column(String(1000))
    alt_text_en: Mapped[str | None] = mapped_column(String(500))
    alt_text_ar: Mapped[str | None] = mapped_column(String(500))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    checksum: Mapped[str | None] = mapped_column(String(255))
    # product.image record id for GALLERY images pulled from Odoo. The PRIMARY-role
    # image has no Odoo record of its own (it comes from product.template.image_1920)
    # so it's matched by (product_id, image_role="PRIMARY") instead and this stays null.
    odoo_image_id: Mapped[int | None] = mapped_column(Integer)

    product: Mapped[CatalogueProduct] = relationship(
        "CatalogueProduct", back_populates="images", foreign_keys=[product_id]
    )
    variant: Mapped[CatalogueProductVariant | None] = relationship(
        "CatalogueProductVariant", foreign_keys=[product_variant_id]
    )
