"""Catalogue product availability.

No stock quantities are seeded (Phase 3 mock data has no inventory concept, D19 is
unresolved) — quantity_available stays null until a real Odoo stock.quant sync exists.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import SourceSyncMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product_variant import CatalogueProductVariant

AVAILABILITY_STATUSES = ("UNKNOWN", "AVAILABLE", "OUT_OF_STOCK", "DISCONTINUED", "PREORDER")


class CatalogueProductAvailability(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_availability"
    __table_args__ = (
        CheckConstraint(
            f"availability_status IN {AVAILABILITY_STATUSES}",
            name="ck_catalogue_product_availability_status",
        ),
        CheckConstraint(
            "quantity_available IS NULL OR quantity_available >= 0",
            name="ck_catalogue_product_availability_quantity_nonneg",
        ),
    )

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_variants.id"), unique=True, nullable=False
    )
    availability_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    quantity_available: Mapped[int | None] = mapped_column(Integer)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    variant: Mapped[CatalogueProductVariant] = relationship(
        "CatalogueProductVariant", back_populates="availability"
    )
