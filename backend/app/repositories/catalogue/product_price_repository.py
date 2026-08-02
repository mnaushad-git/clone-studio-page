from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_price import CatalogueProductPrice
from app.repositories.base import BaseRepository


class ProductPriceRepository(BaseRepository[CatalogueProductPrice]):
    model = CatalogueProductPrice

    def list_for_variant(self, product_variant_id: uuid.UUID) -> Sequence[CatalogueProductPrice]:
        stmt = select(self.model).where(self.model.product_variant_id == product_variant_id)
        return self.session.execute(stmt).scalars().all()

    def get_current(
        self, product_variant_id: uuid.UUID, currency: str
    ) -> CatalogueProductPrice | None:
        stmt = select(self.model).where(
            self.model.product_variant_id == product_variant_id,
            self.model.currency == currency,
            self.model.active.is_(True),
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_current(
        self, product_variant_id: uuid.UUID, currency: str, values: dict[str, Any]
    ) -> tuple[CatalogueProductPrice, bool, bool]:
        """Create-or-update the single active price row for this variant+currency.
        Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin for the
        created/changed contract.
        """
        existing = self.get_current(product_variant_id, currency)
        if existing is None:
            obj = self.model(
                product_variant_id=product_variant_id, currency=currency, active=True, **values
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
