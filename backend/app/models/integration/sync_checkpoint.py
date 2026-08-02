"""Sync checkpoint per (integration, entity_type) pair. No sync job reads or writes
these yet — this only establishes the table a future Odoo sync worker will use.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

CHECKPOINT_STATUSES = ("PENDING", "RUNNING", "SUCCESS", "FAILED")


class IntegrationSyncCheckpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_sync_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "integration_name", "entity_type", name="uq_integration_sync_checkpoints_name_entity"
        ),
        CheckConstraint(
            f"status IN {CHECKPOINT_STATUSES}", name="ck_integration_sync_checkpoints_status"
        ),
    )

    integration_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checkpoint_value: Mapped[str | None] = mapped_column(String(255))
    last_successful_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempted_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
