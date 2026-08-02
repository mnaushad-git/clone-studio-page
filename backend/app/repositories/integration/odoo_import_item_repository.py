from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.integration.odoo_import_item import OdooCatalogueImportItem
from app.repositories.base import BaseRepository


class OdooImportItemRepository(BaseRepository[OdooCatalogueImportItem]):
    model = OdooCatalogueImportItem

    def list_for_run(self, import_run_id: uuid.UUID) -> Sequence[OdooCatalogueImportItem]:
        stmt = select(self.model).where(self.model.import_run_id == import_run_id)
        return self.session.execute(stmt).scalars().all()

    def find_by_external_key(
        self, import_run_id: uuid.UUID, canonical_external_key: str
    ) -> OdooCatalogueImportItem | None:
        stmt = select(self.model).where(
            self.model.import_run_id == import_run_id,
            self.model.canonical_external_key == canonical_external_key,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def find_latest_by_external_key_across_runs(
        self, canonical_external_key: str, *, result_status: str = "SUCCEEDED"
    ) -> OdooCatalogueImportItem | None:
        """Used for ODOO_WRITE_SUCCEEDED_POSTGRES_PENDING recovery: on retry, look up
        whether a prior run already wrote this entity to Odoo (by external key) before
        attempting another create — so a failed PostgreSQL-side commit never causes a
        duplicate Odoo record.
        """
        stmt = (
            select(self.model)
            .where(
                self.model.canonical_external_key == canonical_external_key,
                self.model.result_status == result_status,
                self.model.odoo_record_id.is_not(None),
            )
            .order_by(self.model.completed_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()
