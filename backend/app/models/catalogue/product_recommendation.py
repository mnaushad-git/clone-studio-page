"""Catalogue product recommendation.

Only explicit, canonical recommendations are ever seeded here (source data ships empty
by design, D14) — this table is never populated by arbitrary/generated suggestions.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product import CatalogueProduct

RECOMMENDATION_TYPES = ("MANUAL", "SAME_CATEGORY", "FREQUENTLY_BOUGHT")


class CatalogueProductRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_recommendations"
    __table_args__ = (
        CheckConstraint(
            "product_id != recommended_product_id",
            name="ck_catalogue_product_recommendations_no_self_recommend",
        ),
        CheckConstraint(
            f"recommendation_type IN {RECOMMENDATION_TYPES}",
            name="ck_catalogue_product_recommendations_type",
        ),
        CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_recommendations_display_order_nonneg"
        ),
        UniqueConstraint(
            "product_id",
            "recommended_product_id",
            "recommendation_type",
            name="uq_catalogue_product_recommendations_unique_triplet",
        ),
        Index("ix_catalogue_product_recommendations_product_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), nullable=False
    )
    recommended_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), nullable=False
    )
    recommendation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[CatalogueProduct] = relationship("CatalogueProduct", foreign_keys=[product_id])
    recommended_product: Mapped[CatalogueProduct] = relationship(
        "CatalogueProduct", foreign_keys=[recommended_product_id]
    )
