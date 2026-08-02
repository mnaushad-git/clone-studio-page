from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from app.models.admin.admin_audit_event import AdminAuditEvent
from app.repositories.base import BaseRepository


class AdminAuditRepository(BaseRepository[AdminAuditEvent]):
    model = AdminAuditEvent

    def search(
        self,
        *,
        admin_user_id: object | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[AdminAuditEvent], int]:
        stmt = select(AdminAuditEvent)
        if admin_user_id is not None:
            stmt = stmt.where(AdminAuditEvent.admin_user_id == admin_user_id)
        if action:
            stmt = stmt.where(AdminAuditEvent.action == action)
        if entity_type:
            stmt = stmt.where(AdminAuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AdminAuditEvent.entity_id == entity_id)
        if date_from:
            stmt = stmt.where(AdminAuditEvent.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AdminAuditEvent.created_at <= date_to)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                AdminAuditEvent.admin_email.ilike(pattern)
                | AdminAuditEvent.action.ilike(pattern)
                | AdminAuditEvent.entity_type.ilike(pattern)
            )

        total = self.session.execute(
            select(func.count()).select_from(stmt.with_only_columns(AdminAuditEvent.id).subquery())
        ).scalar_one()

        page_stmt = stmt.order_by(AdminAuditEvent.created_at.desc()).limit(limit).offset(offset)
        items = self.session.execute(page_stmt).scalars().all()
        return items, total
