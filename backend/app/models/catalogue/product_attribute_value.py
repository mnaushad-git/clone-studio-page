"""Catalogue product attribute value.

Join between a `catalogue_product_variants` row and the specific attribute axis/value it
carries (e.g. the "9 INCH x Chocolate" variant gets two rows here: one for the "size"
axis, one for "flavor"). This is the single source of truth for a variant's per-axis
data — both the storefront/checkout-facing display (name/value labels) and the Odoo
`product.attribute`/`product.attribute.value` identity: `attribute_code` is a
stable, app-internal axis key, independent of display-label wording, so relabeling
"Box Size" -> "Cake Size" later doesn't orphan the `odoo_attribute_id`/
`odoo_attribute_value_id` already adopted from a prior Odoo import.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product_variant import CatalogueProductVariant


class CatalogueProductAttributeValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_attribute_values"
    __table_args__ = (
        Index("ix_catalogue_product_attribute_values_variant_id", "variant_id"),
        Index("ix_catalogue_product_attribute_values_attribute_name_en", "attribute_name_en"),
        Index(
            "uq_catalogue_product_attribute_values_variant_axis",
            "variant_id",
            "attribute_code",
            unique=True,
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_variants.id"), nullable=False
    )
    attribute_code: Mapped[str] = mapped_column(String(50), nullable=False)
    attribute_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    value_label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_attribute_id: Mapped[int | None] = mapped_column(Integer)
    odoo_attribute_value_id: Mapped[int | None] = mapped_column(Integer)

    variant: Mapped[CatalogueProductVariant] = relationship(
        "CatalogueProductVariant", back_populates="attribute_values"
    )
