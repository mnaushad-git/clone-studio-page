from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AdminAuditEventOut(BaseModel):
    id: str
    admin_user_id: str | None
    admin_email: str
    action: str
    entity_type: str
    entity_id: str | None
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    reason: str | None
    correlation_id: str | None
    ip_address: str | None
    created_at: datetime


class AdminAuditEventListOut(BaseModel):
    items: list[AdminAuditEventOut]
    total: int
    limit: int
    offset: int
