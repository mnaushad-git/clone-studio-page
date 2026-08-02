from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.integration.odoo_catalogue_sync_item import OdooCatalogueSyncItem
from app.repositories.base import BaseRepository


class OdooCatalogueSyncItemRepository(BaseRepository[OdooCatalogueSyncItem]):
    model = OdooCatalogueSyncItem

    def list_for_run(
        self, sync_run_id: uuid.UUID, *, limit: int = 500
    ) -> Sequence[OdooCatalogueSyncItem]:
        stmt = (
            select(self.model)
            .where(self.model.sync_run_id == sync_run_id)
            .order_by(self.model.created_at)
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()
