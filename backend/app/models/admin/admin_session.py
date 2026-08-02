"""Server-side refresh-token session — enables real logout/revocation instead of a
stateless-only refresh JWT (an admin session can be killed immediately; a bare JWT
can't be revoked before it expires). One row per issued refresh token; rotated on
every /admin/auth/refresh call (the old hash's row is revoked, a new one created).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin_user import AdminUser


class AdminSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (
        Index("ix_admin_sessions_refresh_token_hash", "refresh_token_hash", unique=True),
        Index("ix_admin_sessions_admin_user_id", "admin_user_id"),
    )

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False
    )
    # SHA-256 hex digest of the refresh token — the raw token is never stored, only
    # ever sent to the client once (in the httpOnly cookie).
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    admin_user: Mapped[AdminUser] = relationship("AdminUser", back_populates="sessions")
