"""Catalogue product variant.

Every product has at least one variant (a "default" simple-product variant for
products with no genuine variation). Per-axis attribute data (size, flavor, or any
other Odoo-defined axis) lives exclusively in `catalogue_product_attribute_values`
(via the `attribute_values` relationship below) — that table is the single source of
truth for both the push (Postgres -> Odoo) and pull (Odoo -> Postgres) directions, and
for what the storefront/checkout/admin actually read. There used to be a second,
disconnected `variant_attributes` JSONB column here; it was dropped (migration 0015)
once it became clear the pull-sync never populated it, so the storefront silently saw
no attributes at all for Odoo-originated products — keeping only one representation
makes that class of bug structurally impossible.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import SourceSyncMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product import CatalogueProduct
    from app.models.catalogue.product_attribute_value import CatalogueProductAttributeValue
    from app.models.catalogue.product_availability import CatalogueProductAvailability
    from app.models.catalogue.product_price import CatalogueProductPrice


class CatalogueProductVariant(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_variants"
    __table_args__ = (
        Index("ix_catalogue_product_variants_product_id", "product_id"),
        Index("ix_catalogue_product_variants_odoo_product_variant_id", "odoo_product_variant_id"),
        # Enforces "one default variant must be supportable" as a DB constraint rather
        # than only application logic.
        Index(
            "uq_catalogue_product_variants_one_default_per_product",
            "product_id",
            unique=True,
            postgresql_where="is_default",
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), nullable=False
    )
    external_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    odoo_product_variant_id: Mapped[int | None] = mapped_column(Integer)

    product: Mapped[CatalogueProduct] = relationship("CatalogueProduct", back_populates="variants")
    prices: Mapped[list[CatalogueProductPrice]] = relationship(
        "CatalogueProductPrice", back_populates="variant", cascade="all, delete-orphan"
    )
    availability: Mapped[CatalogueProductAvailability | None] = relationship(
        "CatalogueProductAvailability", back_populates="variant", cascade="all, delete-orphan"
    )
    attribute_values: Mapped[list[CatalogueProductAttributeValue]] = relationship(
        "CatalogueProductAttributeValue", back_populates="variant", cascade="all, delete-orphan"
    )
