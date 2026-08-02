from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_image import CatalogueProductImage
from app.repositories.base import BaseRepository


class ProductImageRepository(BaseRepository[CatalogueProductImage]):
    model = CatalogueProductImage

    def list_for_product(self, product_id: uuid.UUID) -> Sequence[CatalogueProductImage]:
        stmt = (
            select(self.model)
            .where(self.model.product_id == product_id)
            .order_by(self.model.display_order)
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_product_and_path(
        self, product_id: uuid.UUID, original_path: str
    ) -> CatalogueProductImage | None:
        """original_path is the natural idempotent key within a product's images —
        images have no external_key of their own in the canonical seed data."""
        stmt = select(self.model).where(
            self.model.product_id == product_id, self.model.original_path == original_path
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_odoo_image_id(self, odoo_image_id: int) -> CatalogueProductImage | None:
        """Matches a GALLERY image (product.image) pulled from Odoo. PRIMARY images
        have no Odoo record of their own — use get_primary_for_product instead."""
        stmt = select(self.model).where(self.model.odoo_image_id == odoo_image_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_primary_for_product(self, product_id: uuid.UUID) -> CatalogueProductImage | None:
        stmt = select(self.model).where(
            self.model.product_id == product_id, self.model.image_role == "PRIMARY"
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_by_product_and_path(
        self, product_id: uuid.UUID, original_path: str, values: dict[str, Any]
    ) -> tuple[CatalogueProductImage, bool, bool]:
        """Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin."""
        existing = self.get_by_product_and_path(product_id, original_path)
        if existing is None:
            obj = self.model(product_id=product_id, original_path=original_path, **values)
            self.session.add(obj)
            self.session.flush()
            return obj, True, False

        changed = False
        for key, value in values.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True
        if changed:
            self.session.flush()
        return existing, False, changed
