from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.integration.seed_run import CatalogueSeedRun
from app.repositories.base import BaseRepository


class SeedRunRepository(BaseRepository[CatalogueSeedRun]):
    model = CatalogueSeedRun

    def list_recent(self, limit: int = 20) -> Sequence[CatalogueSeedRun]:
        stmt = select(self.model).order_by(self.model.started_at.desc()).limit(limit)
        return self.session.execute(stmt).scalars().all()
