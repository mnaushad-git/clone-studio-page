from __future__ import annotations

from sqlalchemy import select

from app.models.admin.admin_user import AdminUser
from app.repositories.base import BaseRepository


class AdminUserRepository(BaseRepository[AdminUser]):
    model = AdminUser

    def get_by_email(self, email: str) -> AdminUser | None:
        stmt = select(AdminUser).where(AdminUser.email == email.strip().lower())
        return self.session.execute(stmt).scalar_one_or_none()
