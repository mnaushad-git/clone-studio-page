from __future__ import annotations

from sqlalchemy import select

from app.models.admin.admin_session import AdminSession
from app.repositories.base import BaseRepository


class AdminSessionRepository(BaseRepository[AdminSession]):
    model = AdminSession

    def get_by_refresh_token_hash(self, refresh_token_hash: str) -> AdminSession | None:
        stmt = select(AdminSession).where(AdminSession.refresh_token_hash == refresh_token_hash)
        return self.session.execute(stmt).scalar_one_or_none()
