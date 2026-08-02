from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.catalogue.product_variant import CatalogueProductVariant
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
    SkuRepositoryMixin,
)


class ProductVariantRepository(
    ExternalKeyRepositoryMixin[CatalogueProductVariant],
    SkuRepositoryMixin[CatalogueProductVariant],
    ActiveListRepositoryMixin[CatalogueProductVariant],
    BaseRepository[CatalogueProductVariant],
):
    model = CatalogueProductVariant

    def list_by_product(self, product_id: uuid.UUID) -> Sequence[CatalogueProductVariant]:
        stmt = select(self.model).where(self.model.product_id == product_id)
        return self.session.execute(stmt).scalars().all()

    def get_default_for_product(self, product_id: uuid.UUID) -> CatalogueProductVariant | None:
        stmt = select(self.model).where(
            self.model.product_id == product_id, self.model.is_default.is_(True)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_odoo_product_variant_id(
        self, odoo_variant_id: int
    ) -> CatalogueProductVariant | None:
        stmt = select(self.model).where(self.model.odoo_product_variant_id == odoo_variant_id)
        return self.session.execute(stmt).scalar_one_or_none()
