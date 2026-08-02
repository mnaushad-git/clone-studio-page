"""Append-only administrative audit trail. `admin_email` is a snapshot at write time
(kept even if the AdminUser is later deleted — admin_user_id then goes NULL via
ON DELETE SET NULL, but the record of who did it survives). Never stores passwords,
tokens, or secrets — callers are responsible for only passing already-safe
before/after state (see app/services/admin/audit_service.py's docstring).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin_user import AdminUser


class AdminAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "admin_audit_events"
    __table_args__ = (
        Index("ix_admin_audit_events_created_at", "created_at"),
        Index("ix_admin_audit_events_admin_user_id", "admin_user_id"),
        Index("ix_admin_audit_events_entity", "entity_type", "entity_id"),
    )

    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    admin_user: Mapped[AdminUser | None] = relationship("AdminUser")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return (
            f"AdminAuditEvent(id={self.id!s}, action={self.action!r}, "
            f"entity_type={self.entity_type!r})"
        )
