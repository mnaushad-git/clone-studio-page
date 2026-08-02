"""Admin audit-log endpoint (task brief §13). SUPER_ADMIN only — audit history is
sensitive across every domain (order/promo/product/delivery/auth changes), so it
isn't split across the other roles' narrower permissions."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.admin_auth import require_role
from app.api.v1.schemas.admin_audit import AdminAuditEventListOut, AdminAuditEventOut
from app.core.exceptions import ValidationAppError
from app.dependencies import get_db
from app.repositories.admin.admin_audit_repository import AdminAuditRepository

router = APIRouter(prefix="/audit-events", tags=["admin-audit"])


@router.get("", dependencies=[Depends(require_role("SUPER_ADMIN"))])
def list_audit_events(
    session: Session = Depends(get_db),
    admin_user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminAuditEventListOut:
    parsed_admin_user_id: uuid.UUID | None = None
    if admin_user_id:
        try:
            parsed_admin_user_id = uuid.UUID(admin_user_id)
        except ValueError as exc:
            raise ValidationAppError("admin_user_id must be a valid UUID.") from exc

    items, total = AdminAuditRepository(session).search(
        admin_user_id=parsed_admin_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AdminAuditEventListOut(
        items=[
            AdminAuditEventOut(
                id=str(e.id),
                admin_user_id=str(e.admin_user_id) if e.admin_user_id else None,
                admin_email=e.admin_email,
                action=e.action,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                before_state=e.before_state,
                after_state=e.after_state,
                reason=e.reason,
                correlation_id=e.correlation_id,
                ip_address=e.ip_address,
                created_at=e.created_at,
            )
            for e in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
