"""Catalogue category — Odoo-owned identity, Admin-owned presentation (display_order/active).

See docs/catalogue/final-data-ownership.md for the ownership split rationale.
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
    from app.models.catalogue.product import CatalogueProduct


class CatalogueCategory(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_categories"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="ck_catalogue_categories_display_order_nonneg"),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id", name="ck_catalogue_categories_no_self_parent"
        ),
        Index("ix_catalogue_categories_active", "active"),
        Index("ix_catalogue_categories_parent_id", "parent_id"),
        Index("ix_catalogue_categories_odoo_category_id", "odoo_category_id"),
    )

    external_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_ar: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_categories.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    odoo_category_id: Mapped[int | None] = mapped_column(Integer)

    parent: Mapped[CatalogueCategory | None] = relationship(
        "CatalogueCategory", remote_side="CatalogueCategory.id", back_populates="children"
    )
    children: Mapped[list[CatalogueCategory]] = relationship(
        "CatalogueCategory", back_populates="parent"
    )
    products: Mapped[list[CatalogueProduct]] = relationship(
        "CatalogueProduct", back_populates="category"
    )
