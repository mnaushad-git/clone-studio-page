from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.admin.promo_code import PromoCode
from app.repositories.base import BaseRepository


class PromoCodeRepository(BaseRepository[PromoCode]):
    model = PromoCode

    def get_by_code(self, code: str) -> PromoCode | None:
        stmt = select(PromoCode).where(PromoCode.code == code.strip().upper())
        return self.session.execute(stmt).scalar_one_or_none()

    def search(
        self,
        *,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[PromoCode], int]:
        stmt = select(PromoCode)
        if is_active is not None:
            stmt = stmt.where(PromoCode.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip().upper()}%"
            stmt = stmt.where(PromoCode.code.ilike(pattern))

        total = self.session.execute(
            select(func.count()).select_from(stmt.with_only_columns(PromoCode.id).subquery())
        ).scalar_one()

        page_stmt = stmt.order_by(PromoCode.created_at.desc()).limit(limit).offset(offset)
        items = self.session.execute(page_stmt).scalars().all()
        return items, total

    def delete(self, promo: PromoCode) -> None:
        self.session.delete(promo)
        self.session.flush()
