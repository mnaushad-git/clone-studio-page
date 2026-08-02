from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.repositories.base import BaseRepository


class OdooCatalogueSyncRunRepository(BaseRepository[OdooCatalogueSyncRun]):
    model = OdooCatalogueSyncRun

    def list_recent(self, limit: int = 20) -> Sequence[OdooCatalogueSyncRun]:
        stmt = select(self.model).order_by(self.model.started_at.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def get_by_id_str(self, run_id: str) -> OdooCatalogueSyncRun | None:
        try:
            parsed = uuid.UUID(run_id)
        except ValueError:
            return None
        return self.get_by_id(parsed)

    def mark_status(
        self, run: OdooCatalogueSyncRun, status: str, **extra_values: Any
    ) -> OdooCatalogueSyncRun:
        return self.update(run, status=status, **extra_values)
