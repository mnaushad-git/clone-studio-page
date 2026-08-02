"""One row per category/product/variant/price/image/availability record considered by
an Odoo catalogue sync run — the granular audit trail odoo_catalogue_sync_runs'
summary counts are rolled up from. The reverse-direction counterpart of
odoo_catalogue_import_items.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SYNC_ENTITY_TYPES = (
    "CATEGORY",
    "PRODUCT_TEMPLATE",
    "PRODUCT_VARIANT",
    "PRODUCT_PRICE",
    "PRODUCT_IMAGE",
    "PRODUCT_AVAILABILITY",
)
SYNC_MATCH_STRATEGIES = ("ODOO_ID", "NATURAL_KEY", "CREATED")
SYNC_ACTIONS = ("CREATE", "UPDATE", "SKIP_UNCHANGED", "FAILED")
SYNC_ITEM_RESULT_STATUSES = ("PENDING", "SUCCEEDED", "FAILED")


class OdooCatalogueSyncItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "odoo_catalogue_sync_items"
    __table_args__ = (
        CheckConstraint(
            f"entity_type IN {SYNC_ENTITY_TYPES}", name="ck_odoo_sync_items_entity_type"
        ),
        CheckConstraint(
            f"match_strategy IS NULL OR match_strategy IN {SYNC_MATCH_STRATEGIES}",
            name="ck_odoo_sync_items_match_strategy",
        ),
        CheckConstraint(f"action IN {SYNC_ACTIONS}", name="ck_odoo_sync_items_action"),
        CheckConstraint(
            f"result_status IN {SYNC_ITEM_RESULT_STATUSES}", name="ck_odoo_sync_items_result_status"
        ),
        Index("ix_odoo_sync_items_sync_run_id", "sync_run_id"),
        Index("ix_odoo_sync_items_odoo_record_id", "odoo_record_id"),
        Index("ix_odoo_sync_items_postgres_entity_id", "postgres_entity_id"),
        Index("ix_odoo_sync_items_result_status", "result_status"),
        Index("ix_odoo_sync_items_entity_type_model", "entity_type", "odoo_model"),
    )

    sync_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("odoo_catalogue_sync_runs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    odoo_model: Mapped[str] = mapped_column(String(100), nullable=False)
    odoo_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    postgres_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    match_strategy: Mapped[str | None] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    before_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    odoo_write_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
