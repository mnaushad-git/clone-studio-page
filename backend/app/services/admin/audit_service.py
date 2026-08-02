"""Records administrative audit events (task brief §13). One call site used by every
mutating admin endpoint — flushes but never commits (the caller's transaction owns
that, same session-lifecycle convention as every other repository/service here).

Callers must never pass a password, token, or other secret into `before`/`after` —
this service does not attempt to redact those itself (there is no reliable way to
detect "this JSON blob contains a secret" after the fact); it only guarantees the
columns that structurally can't hold one (action/entity_type/ids/reason) are safe.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.models.admin.admin_audit_event import AdminAuditEvent
from app.models.admin.admin_user import AdminUser
from app.repositories.admin.admin_audit_repository import AdminAuditRepository


def _json_safe(value: Any) -> Any:
    """before_state/after_state land in a JSONB column, but callers pass raw ORM
    attribute values (Decimal for Numeric columns, datetime, UUID) — none of those
    are JSON-serializable as-is, so normalize recursively before it ever reaches the
    session."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AdminAuditRepository(session)

    def record(
        self,
        *,
        admin: AdminUser | None,
        admin_email: str,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str | None = None,
        request: Request | None = None,
    ) -> AdminAuditEvent:
        correlation_id = getattr(request.state, "correlation_id", None) if request else None
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None

        event = AdminAuditEvent(
            admin_user_id=admin.id if admin else None,
            admin_email=admin_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=_json_safe(before) if before is not None else None,
            after_state=_json_safe(after) if after is not None else None,
            reason=reason,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return self.repo.create(event)
