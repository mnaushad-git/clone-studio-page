"""Storefront section-to-product assignment."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StorefrontSectionProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "storefront_section_products"
    __table_args__ = (
        CheckConstraint(
            "display_order >= 0", name="ck_storefront_section_products_display_order_nonneg"
        ),
        UniqueConstraint(
            "section_id", "product_id", name="uq_storefront_section_products_section_product"
        ),
    )

    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storefront_sections.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
