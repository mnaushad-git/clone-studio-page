from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.integration.odoo_import_run import OdooCatalogueImportRun
from app.repositories.base import BaseRepository


class OdooImportRunRepository(BaseRepository[OdooCatalogueImportRun]):
    model = OdooCatalogueImportRun

    def list_recent(self, limit: int = 20) -> Sequence[OdooCatalogueImportRun]:
        stmt = select(self.model).order_by(self.model.started_at.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def get_by_id_str(self, run_id: str) -> OdooCatalogueImportRun | None:
        try:
            parsed = uuid.UUID(run_id)
        except ValueError:
            return None
        return self.get_by_id(parsed)

    def mark_status(
        self, run: OdooCatalogueImportRun, status: str, **extra_values: Any
    ) -> OdooCatalogueImportRun:
        return self.update(run, status=status, **extra_values)
