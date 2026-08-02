from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.storefront.section_product import StorefrontSectionProduct
from app.repositories.base import BaseRepository


class StorefrontSectionProductRepository(BaseRepository[StorefrontSectionProduct]):
    model = StorefrontSectionProduct

    def list_for_section(self, section_id: uuid.UUID) -> Sequence[StorefrontSectionProduct]:
        stmt = (
            select(self.model)
            .where(self.model.section_id == section_id)
            .order_by(self.model.display_order)
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_section_and_product(
        self, section_id: uuid.UUID, product_id: uuid.UUID
    ) -> StorefrontSectionProduct | None:
        stmt = select(self.model).where(
            self.model.section_id == section_id, self.model.product_id == product_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert(
        self, section_id: uuid.UUID, product_id: uuid.UUID, values: dict[str, Any]
    ) -> tuple[StorefrontSectionProduct, bool, bool]:
        """Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin."""
        existing = self.get_by_section_and_product(section_id, product_id)
        if existing is None:
            obj = self.model(section_id=section_id, product_id=product_id, **values)
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
