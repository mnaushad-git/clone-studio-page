"""Odoo catalogue import run — one row per invocation of
app.scripts.import_odoo_catalogue, in any mode. Append-mostly audit log: a run's
status/counts are updated as it progresses, but a run row is never deleted.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

IMPORT_MODES = ("VALIDATE", "PLAN", "DRY_RUN", "APPLY", "ROLLBACK_PLAN")
IMPORT_RUN_STATUSES = (
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
    "PARTIALLY_COMPLETED",
    "ROLLBACK_REQUIRED",
)


class OdooCatalogueImportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "odoo_catalogue_import_runs"
    __table_args__ = (
        CheckConstraint(f"mode IN {IMPORT_MODES}", name="ck_odoo_import_runs_mode"),
        CheckConstraint(f"status IN {IMPORT_RUN_STATUSES}", name="ck_odoo_import_runs_status"),
    )

    environment_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    odoo_version: Mapped[str] = mapped_column(String(100), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    source_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    approval_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    import_plan_checksum: Mapped[str] = mapped_column(String(255), nullable=False)

    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    planned_create_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_skip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    actual_create_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_skip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
