"""Catalogue product price.

price_includes_tax is intentionally nullable and never assumed: the current storefront
has an unresolved VAT-inclusive-vs-exclusive contradiction (PDP copy vs. checkout math,
D21 in docs/catalogue/catalogue-decisions.json). This table preserves that ambiguity
rather than encoding either interpretation as fact.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import SourceSyncMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.catalogue.product_variant import CatalogueProductVariant


class CatalogueProductPrice(UUIDPrimaryKeyMixin, SourceSyncMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_product_prices"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_catalogue_product_prices_amount_nonneg"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_catalogue_product_prices_valid_range",
        ),
        Index("ix_catalogue_product_prices_variant_id", "product_variant_id"),
        # One current active price per variant+currency, enforced by the database.
        Index(
            "uq_catalogue_product_prices_one_active_per_variant_currency",
            "product_variant_id",
            "currency",
            unique=True,
            postgresql_where="active",
        ),
    )

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_variants.id"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_reference: Mapped[str | None] = mapped_column(String(255))
    price_includes_tax: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    odoo_pricelist_id: Mapped[int | None] = mapped_column(Integer)

    variant: Mapped[CatalogueProductVariant] = relationship(
        "CatalogueProductVariant", back_populates="prices"
    )
