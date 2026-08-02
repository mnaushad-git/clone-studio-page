"""Catalogue moment — PostgreSQL/Admin-owned vocabulary, independent of Odoo categories."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CatalogueMoment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "catalogue_moments"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="ck_catalogue_moments_display_order_nonneg"),
        Index("ix_catalogue_moments_active", "active"),
    )

    external_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(Text)
    description_ar: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
