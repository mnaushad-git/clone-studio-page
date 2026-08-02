"""Odoo catalogue sync run — one row per invocation of the Odoo -> PostgreSQL
catalogue pull (scheduled Celery beat tick or an admin "Sync now" trigger). The
reverse-direction counterpart of odoo_catalogue_import_runs (which audits the
PostgreSQL -> Odoo push). Append-mostly: a run's status/counts are updated as it
progresses, but a run row is never deleted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SYNC_TRIGGERS = ("SCHEDULED", "MANUAL")
SYNC_RUN_STATUSES = ("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "PARTIALLY_COMPLETED")


class OdooCatalogueSyncRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "odoo_catalogue_sync_runs"
    __table_args__ = (
        CheckConstraint(f"trigger IN {SYNC_TRIGGERS}", name="ck_odoo_sync_runs_trigger"),
        CheckConstraint(f"status IN {SYNC_RUN_STATUSES}", name="ck_odoo_sync_runs_status"),
    )

    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    full_resync: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    total_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counts_by_entity_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_summary: Mapped[str | None] = mapped_column(Text)
