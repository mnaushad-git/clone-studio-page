"""odoo catalogue import runs

Creates the Phase 5 Odoo catalogue import audit tables: one row per
import_odoo_catalogue invocation (odoo_catalogue_import_runs) and one row per
category/product/variant/image/XML-ID it considered (odoo_catalogue_import_items).
No Odoo write happens anywhere in this migration — this only creates the PostgreSQL
bookkeeping the importer (app/services/catalogue/odoo_import_service.py) writes to.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_TIMESTAMP_COLUMNS = (
    sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    ),
)

_IMPORT_MODES = "('VALIDATE', 'PLAN', 'DRY_RUN', 'APPLY', 'ROLLBACK_PLAN')"
_IMPORT_RUN_STATUSES = (
    "('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'BLOCKED', "
    "'PARTIALLY_COMPLETED', 'ROLLBACK_REQUIRED')"
)
_ENTITY_TYPES = (
    "('CATEGORY', 'PRODUCT_TEMPLATE', 'PRODUCT_VARIANT', 'PRODUCT_IMAGE', 'EXTERNAL_XML_ID')"
)
_PLANNED_ACTIONS = "('CREATE', 'UPDATE', 'MATCH', 'SKIP', 'BLOCKED')"
_RESULT_STATUSES = "('PENDING', 'SUCCEEDED', 'FAILED', 'SKIPPED', 'BLOCKED', 'ROLLBACK_REQUIRED')"


def upgrade() -> None:
    op.create_table(
        "odoo_catalogue_import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("odoo_version", sa.String(length=100), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_checksum", sa.String(length=255), nullable=False),
        sa.Column("approval_checksum", sa.String(length=255), nullable=False),
        sa.Column("import_plan_checksum", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_create_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("planned_update_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("planned_skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("planned_blocked_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_create_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_update_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correlation_id", sa.String(length=255), nullable=False),
        sa.Column("initiated_by", sa.String(length=255), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.CheckConstraint(f"mode IN {_IMPORT_MODES}", name="ck_odoo_import_runs_mode"),
        sa.CheckConstraint(f"status IN {_IMPORT_RUN_STATUSES}", name="ck_odoo_import_runs_status"),
    )

    op.create_table(
        "odoo_catalogue_import_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("canonical_external_key", sa.String(length=255), nullable=False),
        sa.Column("canonical_sku", sa.String(length=64), nullable=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=True),
        sa.Column("odoo_model", sa.String(length=100), nullable=False),
        sa.Column("planned_action", sa.String(length=20), nullable=False),
        sa.Column("actual_action", sa.String(length=20), nullable=True),
        sa.Column("odoo_record_id", sa.Integer(), nullable=True),
        sa.Column("external_xml_id", sa.String(length=255), nullable=True),
        sa.Column("before_state_json", postgresql.JSONB(), nullable=True),
        sa.Column("proposed_values_json", postgresql.JSONB(), nullable=True),
        sa.Column("written_values_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["import_run_id"], ["odoo_catalogue_import_runs.id"]),
        sa.CheckConstraint(
            f"entity_type IN {_ENTITY_TYPES}", name="ck_odoo_import_items_entity_type"
        ),
        sa.CheckConstraint(
            f"planned_action IN {_PLANNED_ACTIONS}", name="ck_odoo_import_items_planned_action"
        ),
        sa.CheckConstraint(
            f"actual_action IS NULL OR actual_action IN {_PLANNED_ACTIONS}",
            name="ck_odoo_import_items_actual_action",
        ),
        sa.CheckConstraint(
            f"result_status IN {_RESULT_STATUSES}", name="ck_odoo_import_items_result_status"
        ),
    )
    op.create_index(
        "ix_odoo_import_items_import_run_id", "odoo_catalogue_import_items", ["import_run_id"]
    )
    op.create_index(
        "ix_odoo_import_items_canonical_external_key",
        "odoo_catalogue_import_items",
        ["canonical_external_key"],
    )
    op.create_index(
        "ix_odoo_import_items_canonical_sku", "odoo_catalogue_import_items", ["canonical_sku"]
    )
    op.create_index(
        "ix_odoo_import_items_odoo_record_id", "odoo_catalogue_import_items", ["odoo_record_id"]
    )
    op.create_index(
        "ix_odoo_import_items_external_xml_id", "odoo_catalogue_import_items", ["external_xml_id"]
    )
    op.create_index(
        "ix_odoo_import_items_result_status", "odoo_catalogue_import_items", ["result_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_odoo_import_items_result_status", table_name="odoo_catalogue_import_items")
    op.drop_index("ix_odoo_import_items_external_xml_id", table_name="odoo_catalogue_import_items")
    op.drop_index("ix_odoo_import_items_odoo_record_id", table_name="odoo_catalogue_import_items")
    op.drop_index("ix_odoo_import_items_canonical_sku", table_name="odoo_catalogue_import_items")
    op.drop_index(
        "ix_odoo_import_items_canonical_external_key", table_name="odoo_catalogue_import_items"
    )
    op.drop_index("ix_odoo_import_items_import_run_id", table_name="odoo_catalogue_import_items")
    op.drop_table("odoo_catalogue_import_items")
    op.drop_table("odoo_catalogue_import_runs")
