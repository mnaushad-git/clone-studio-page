from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.catalogue.product_attribute_value import CatalogueProductAttributeValue
from app.repositories.base import BaseRepository


class ProductAttributeValueRepository(BaseRepository[CatalogueProductAttributeValue]):
    model = CatalogueProductAttributeValue

    def list_by_variant(self, variant_id: uuid.UUID) -> Sequence[CatalogueProductAttributeValue]:
        stmt = select(self.model).where(self.model.variant_id == variant_id)
        return self.session.execute(stmt).scalars().all()

    def list_all(self) -> Sequence[CatalogueProductAttributeValue]:
        return self.session.execute(select(self.model)).scalars().all()

    def get_by_variant_and_code(
        self, variant_id: uuid.UUID, attribute_code: str
    ) -> CatalogueProductAttributeValue | None:
        stmt = select(self.model).where(
            self.model.variant_id == variant_id, self.model.attribute_code == attribute_code
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_odoo_attribute_id(
        self, odoo_attribute_id: int
    ) -> CatalogueProductAttributeValue | None:
        """Any single row already carrying this Odoo attribute id — used by the pull
        sync to reuse the same attribute_code/attribute_name_en every time this Odoo
        attribute is encountered again (on a different product/variant), rather than
        minting a fresh code per occurrence.
        """
        stmt = (
            select(self.model)
            .where(self.model.odoo_attribute_id == odoo_attribute_id)
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_attribute_name(
        self, attribute_name_en: str
    ) -> Sequence[CatalogueProductAttributeValue]:
        """Every row across every product/variant carrying this attribute name — used to
        fan-out an adopted `odoo_attribute_id` to every row sharing that shared, N:1 Odoo
        attribute (unlike category/product ids, which are 1:1 and never fan out).
        """
        stmt = select(self.model).where(self.model.attribute_name_en == attribute_name_en)
        return self.session.execute(stmt).scalars().all()

    def list_by_attribute_name_and_value(
        self, attribute_name_en: str, value_label_en: str
    ) -> Sequence[CatalogueProductAttributeValue]:
        """Every row sharing this exact (attribute, value) pair — same N:1 fan-out
        rationale as list_by_attribute_name, scoped to one specific value.
        """
        stmt = select(self.model).where(
            self.model.attribute_name_en == attribute_name_en,
            self.model.value_label_en == value_label_en,
        )
        return self.session.execute(stmt).scalars().all()

    def upsert_for_variant(
        self, variant_id: uuid.UUID, attribute_code: str, values: dict[str, Any]
    ) -> tuple[CatalogueProductAttributeValue, bool, bool]:
        """Create-or-update by (variant_id, attribute_code) — the axis is unique per
        variant (see the unique index on this table). Mirrors
        `ExternalKeyRepositoryMixin.upsert_by_external_key`'s created/changed contract.
        """
        existing = self.get_by_variant_and_code(variant_id, attribute_code)
        if existing is None:
            obj = self.model(variant_id=variant_id, attribute_code=attribute_code, **values)
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
