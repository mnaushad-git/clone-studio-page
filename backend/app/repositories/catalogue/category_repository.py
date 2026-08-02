from __future__ import annotations

from typing import ClassVar

from sqlalchemy import select

from app.models.catalogue.category import CatalogueCategory
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
    SlugRepositoryMixin,
)


class CategoryRepository(
    ExternalKeyRepositoryMixin[CatalogueCategory],
    SlugRepositoryMixin[CatalogueCategory],
    ActiveListRepositoryMixin[CatalogueCategory],
    BaseRepository[CatalogueCategory],
):
    model = CatalogueCategory
    order_by: ClassVar[tuple] = (CatalogueCategory.display_order,)

    def get_by_odoo_category_id(self, odoo_category_id: int) -> CatalogueCategory | None:
        stmt = select(self.model).where(self.model.odoo_category_id == odoo_category_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> CatalogueCategory | None:
        stmt = select(self.model).where(self.model.code == code)
        return self.session.execute(stmt).scalar_one_or_none()
