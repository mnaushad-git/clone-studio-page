from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_recommendation import CatalogueProductRecommendation
from app.repositories.base import BaseRepository


class ProductRecommendationRepository(BaseRepository[CatalogueProductRecommendation]):
    model = CatalogueProductRecommendation

    def list_for_product(self, product_id: uuid.UUID) -> Sequence[CatalogueProductRecommendation]:
        stmt = (
            select(self.model)
            .where(self.model.product_id == product_id)
            .order_by(self.model.display_order)
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_triplet(
        self, product_id: uuid.UUID, recommended_product_id: uuid.UUID, recommendation_type: str
    ) -> CatalogueProductRecommendation | None:
        stmt = select(self.model).where(
            self.model.product_id == product_id,
            self.model.recommended_product_id == recommended_product_id,
            self.model.recommendation_type == recommendation_type,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_by_triplet(
        self,
        product_id: uuid.UUID,
        recommended_product_id: uuid.UUID,
        recommendation_type: str,
        values: dict[str, Any],
    ) -> tuple[CatalogueProductRecommendation, bool, bool]:
        """Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin."""
        existing = self.get_by_triplet(product_id, recommended_product_id, recommendation_type)
        if existing is None:
            obj = self.model(
                product_id=product_id,
                recommended_product_id=recommended_product_id,
                recommendation_type=recommendation_type,
                **values,
            )
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
