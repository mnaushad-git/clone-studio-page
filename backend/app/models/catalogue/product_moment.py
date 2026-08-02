"""Product-to-moment mapping. Composite primary key (product_id, moment_id) — no
surrogate id, since the pair itself is the natural, sufficient identifier.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class CatalogueProductMoment(TimestampMixin, Base):
    __tablename__ = "catalogue_product_moments"
    __table_args__ = (
        CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_moments_display_order_nonneg"
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id"), primary_key=True
    )
    moment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_moments.id"), primary_key=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
