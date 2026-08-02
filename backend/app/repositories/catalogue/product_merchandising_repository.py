from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.repositories.base import BaseRepository


class ProductMerchandisingRepository(BaseRepository[CatalogueProductMerchandising]):
    model = CatalogueProductMerchandising

    def get_for_product(self, product_id: uuid.UUID) -> CatalogueProductMerchandising | None:
        stmt = select(self.model).where(self.model.product_id == product_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_for_product(
        self, product_id: uuid.UUID, values: dict[str, Any]
    ) -> tuple[CatalogueProductMerchandising, bool, bool]:
        """One merchandising row per product (enforced by a unique constraint too).
        Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin.
        """
        existing = self.get_for_product(product_id)
        if existing is None:
            obj = self.model(product_id=product_id, **values)
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
