"""One row per category/product/variant/image/XML-ID considered by an Odoo catalogue
import run — the granular audit trail odoo_catalogue_import_runs' summary counts are
rolled up from, and what app.scripts.plan_odoo_catalogue_rollback reads to classify
rollback actions.
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

ENTITY_TYPES = (
    "CATEGORY",
    "PRODUCT_TEMPLATE",
    "PRODUCT_VARIANT",
    "PRODUCT_IMAGE",
    "EXTERNAL_XML_ID",
    "PRODUCT_ATTRIBUTE",
    "PRODUCT_ATTRIBUTE_VALUE",
)
PLANNED_ACTIONS = ("CREATE", "UPDATE", "MATCH", "SKIP", "BLOCKED")
RESULT_STATUSES = ("PENDING", "SUCCEEDED", "FAILED", "SKIPPED", "BLOCKED", "ROLLBACK_REQUIRED")


class OdooCatalogueImportItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "odoo_catalogue_import_items"
    __table_args__ = (
        CheckConstraint(f"entity_type IN {ENTITY_TYPES}", name="ck_odoo_import_items_entity_type"),
        CheckConstraint(
            f"planned_action IN {PLANNED_ACTIONS}", name="ck_odoo_import_items_planned_action"
        ),
        CheckConstraint(
            f"actual_action IS NULL OR actual_action IN {PLANNED_ACTIONS}",
            name="ck_odoo_import_items_actual_action",
        ),
        CheckConstraint(
            f"result_status IN {RESULT_STATUSES}", name="ck_odoo_import_items_result_status"
        ),
        Index("ix_odoo_import_items_import_run_id", "import_run_id"),
        Index("ix_odoo_import_items_canonical_external_key", "canonical_external_key"),
        Index("ix_odoo_import_items_canonical_sku", "canonical_sku"),
        Index("ix_odoo_import_items_odoo_record_id", "odoo_record_id"),
        Index("ix_odoo_import_items_external_xml_id", "external_xml_id"),
        Index("ix_odoo_import_items_result_status", "result_status"),
    )

    import_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("odoo_catalogue_import_runs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    canonical_external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_sku: Mapped[str | None] = mapped_column(String(64))
    canonical_name: Mapped[str | None] = mapped_column(String(255))
    odoo_model: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_action: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_action: Mapped[str | None] = mapped_column(String(20))
    odoo_record_id: Mapped[int | None] = mapped_column(Integer)
    external_xml_id: Mapped[str | None] = mapped_column(String(255))
    before_state_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    proposed_values_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    written_values_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
