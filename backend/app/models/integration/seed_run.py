"""Catalogue seed-run history — an append-only audit log, so no updated_at column."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin

SEED_RUN_STATUSES = ("RUNNING", "SUCCESS", "FAILED", "DRY_RUN")


class CatalogueSeedRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "catalogue_seed_runs"
    __table_args__ = (
        CheckConstraint(f"status IN {SEED_RUN_STATUSES}", name="ck_catalogue_seed_runs_status"),
    )

    seed_version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
