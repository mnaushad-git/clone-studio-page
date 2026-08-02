"""Order line item — a price/name snapshot taken at order-creation time.

Deliberately denormalized (sku/name_en/unit_price/attributes_json copied, not joined
live): once an order is placed its receipt must never change even if the catalogue
product is later repriced, renamed, has its variant deleted, or has its attribute
names relabeled. product_id/product_variant_id are kept for traceability but are
nullable and ON DELETE SET NULL — losing the FK must never lose the line item.

attributes_json replaced the old fixed `size_label`/`flavor` columns (migration 0015)
— a product's variant can now have any number of named axes (any Odoo-defined
attribute, not just size/flavor), so the snapshot is a list, not two fixed columns.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.orders.order import Order


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_nonneg"),
        CheckConstraint("line_total >= 0", name="ck_order_items_line_total_nonneg"),
        Index("ix_order_items_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_products.id", ondelete="SET NULL")
    )
    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalogue_product_variants.id", ondelete="SET NULL")
    )

    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    # [{"code": "size", "name_en": "Cake Size", "value_label_en": "9 INCH"}, ...] — one
    # entry per axis selected at order time, snapshotted from the resolved variant's
    # catalogue_product_attribute_values rows (see order_service.py).
    attributes_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    inscription: Mapped[str | None] = mapped_column(String(255))

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
