from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogue.product_recipient import CatalogueProductRecipient


class ProductRecipientRepository:
    """Composite-key join table (product_id, recipient_id) — no surrogate id, so this
    doesn't extend BaseRepository's single-column get_by_id.
    """

    model = CatalogueProductRecipient

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, product_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> CatalogueProductRecipient | None:
        return self.session.get(
            self.model, {"product_id": product_id, "recipient_id": recipient_id}
        )

    def list_for_product(self, product_id: uuid.UUID) -> Sequence[CatalogueProductRecipient]:
        stmt = select(self.model).where(self.model.product_id == product_id)
        return self.session.execute(stmt).scalars().all()

    def list_for_products(
        self, product_ids: Sequence[uuid.UUID]
    ) -> Sequence[CatalogueProductRecipient]:
        """Batch variant of list_for_product — one query for a whole page of products
        instead of one query per product."""
        if not product_ids:
            return []
        stmt = select(self.model).where(self.model.product_id.in_(product_ids))
        return self.session.execute(stmt).scalars().all()

    def upsert(
        self, product_id: uuid.UUID, recipient_id: uuid.UUID, values: dict[str, Any]
    ) -> tuple[CatalogueProductRecipient, bool, bool]:
        """Returns (row, created, changed) — see base.ExternalKeyRepositoryMixin."""
        existing = self.get(product_id, recipient_id)
        if existing is None:
            obj = self.model(product_id=product_id, recipient_id=recipient_id, **values)
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
