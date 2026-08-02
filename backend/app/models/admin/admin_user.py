"""Admin/staff identity — separate from any customer identity (there is none yet).
Replaces the Admin Portal's client-editable `staff` array (src/lib/admin-store.ts):
role is enforced server-side by app/api/deps/admin_auth.py's require_role dependency,
never trusted from a client-submitted value, closing the self-service privilege
escalation gap flagged in docs/current-state/gap-analysis.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin_session import AdminSession

# Minimum MVP role set (task brief §2) — deliberately not the frontend mock's
# owner/admin/manager/support/kitchen model; see the Admin Portal MVP plan's "Key
# decisions" §2 for why. Enforced with a plain require_role(*roles) dependency, no
# RBAC engine.
ADMIN_ROLES = ("SUPER_ADMIN", "OPERATIONS_ADMIN", "CATALOGUE_ADMIN", "SUPPORT_ADMIN")


class AdminUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"
    __table_args__ = (
        CheckConstraint(f"role IN {ADMIN_ROLES}", name="ck_admin_users_role"),
        CheckConstraint("failed_login_count >= 0", name="ck_admin_users_failed_login_nonneg"),
        Index("ix_admin_users_email", "email", unique=True),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[AdminSession]] = relationship(
        "AdminSession", back_populates="admin_user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"AdminUser(id={self.id!s}, email={self.email!r}, role={self.role!r})"
