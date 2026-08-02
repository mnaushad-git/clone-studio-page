from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_availability import CatalogueProductAvailability
from app.repositories.base import BaseRepository


class ProductAvailabilityRepository(BaseRepository[CatalogueProductAvailability]):
    model = CatalogueProductAvailability

    def get_for_variant(self, product_variant_id: uuid.UUID) -> CatalogueProductAvailability | None:
        stmt = select(self.model).where(self.model.product_variant_id == product_variant_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_for_variant(
        self, product_variant_id: uuid.UUID, values: dict[str, Any]
    ) -> tuple[CatalogueProductAvailability, bool, bool]:
        """Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin."""
        existing = self.get_for_variant(product_variant_id)
        if existing is None:
            obj = self.model(product_variant_id=product_variant_id, **values)
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
