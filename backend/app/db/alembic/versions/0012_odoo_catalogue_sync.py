"""odoo catalogue sync

Creates the Odoo -> PostgreSQL catalogue pull-sync audit tables
(odoo_catalogue_sync_runs/items) — the reverse-direction counterpart of
odoo_catalogue_import_runs/items (which audits the PostgreSQL -> Odoo push). Also adds
two small existing-table fixes needed for the sync's matching logic: an odoo_image_id
column on catalogue_product_images (for matching product.image gallery records) and
the missing index on catalogue_product_variants.odoo_product_variant_id (the column
already existed but was never indexed, and the sync looks it up on every run).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
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

_SYNC_TRIGGERS = "('SCHEDULED', 'MANUAL')"
_SYNC_RUN_STATUSES = "('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'PARTIALLY_COMPLETED')"
_SYNC_ENTITY_TYPES = (
    "('CATEGORY', 'PRODUCT_TEMPLATE', 'PRODUCT_VARIANT', 'PRODUCT_PRICE', "
    "'PRODUCT_IMAGE', 'PRODUCT_AVAILABILITY')"
)
_SYNC_MATCH_STRATEGIES = "('ODOO_ID', 'NATURAL_KEY', 'CREATED')"
_SYNC_ACTIONS = "('CREATE', 'UPDATE', 'SKIP_UNCHANGED', 'FAILED')"
_SYNC_ITEM_RESULT_STATUSES = "('PENDING', 'SUCCEEDED', 'FAILED')"


def upgrade() -> None:
    op.create_table(
        "odoo_catalogue_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("full_resync", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=False),
        sa.Column("initiated_by", sa.String(length=255), nullable=False),
        sa.Column("total_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("counts_by_entity_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.CheckConstraint(f"trigger IN {_SYNC_TRIGGERS}", name="ck_odoo_sync_runs_trigger"),
        sa.CheckConstraint(f"status IN {_SYNC_RUN_STATUSES}", name="ck_odoo_sync_runs_status"),
    )
    op.create_index("ix_odoo_sync_runs_started_at", "odoo_catalogue_sync_runs", ["started_at"])

    op.create_table(
        "odoo_catalogue_sync_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("odoo_model", sa.String(length=100), nullable=False),
        sa.Column("odoo_record_id", sa.Integer(), nullable=False),
        sa.Column("postgres_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_strategy", sa.String(length=20), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("before_state_json", postgresql.JSONB(), nullable=True),
        sa.Column("after_state_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("odoo_write_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["sync_run_id"], ["odoo_catalogue_sync_runs.id"]),
        sa.CheckConstraint(
            f"entity_type IN {_SYNC_ENTITY_TYPES}", name="ck_odoo_sync_items_entity_type"
        ),
        sa.CheckConstraint(
            f"match_strategy IS NULL OR match_strategy IN {_SYNC_MATCH_STRATEGIES}",
            name="ck_odoo_sync_items_match_strategy",
        ),
        sa.CheckConstraint(f"action IN {_SYNC_ACTIONS}", name="ck_odoo_sync_items_action"),
        sa.CheckConstraint(
            f"result_status IN {_SYNC_ITEM_RESULT_STATUSES}",
            name="ck_odoo_sync_items_result_status",
        ),
    )
    op.create_index("ix_odoo_sync_items_sync_run_id", "odoo_catalogue_sync_items", ["sync_run_id"])
    op.create_index(
        "ix_odoo_sync_items_odoo_record_id", "odoo_catalogue_sync_items", ["odoo_record_id"]
    )
    op.create_index(
        "ix_odoo_sync_items_postgres_entity_id", "odoo_catalogue_sync_items", ["postgres_entity_id"]
    )
    op.create_index(
        "ix_odoo_sync_items_result_status", "odoo_catalogue_sync_items", ["result_status"]
    )
    op.create_index(
        "ix_odoo_sync_items_entity_type_model",
        "odoo_catalogue_sync_items",
        ["entity_type", "odoo_model"],
    )

    op.add_column(
        "catalogue_product_images", sa.Column("odoo_image_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        "ix_catalogue_product_images_odoo_image_id",
        "catalogue_product_images",
        ["odoo_image_id"],
    )

    op.create_index(
        "ix_catalogue_product_variants_odoo_product_variant_id",
        "catalogue_product_variants",
        ["odoo_product_variant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalogue_product_variants_odoo_product_variant_id",
        table_name="catalogue_product_variants",
    )

    op.drop_index(
        "ix_catalogue_product_images_odoo_image_id", table_name="catalogue_product_images"
    )
    op.drop_column("catalogue_product_images", "odoo_image_id")

    op.drop_index("ix_odoo_sync_items_entity_type_model", table_name="odoo_catalogue_sync_items")
    op.drop_index("ix_odoo_sync_items_result_status", table_name="odoo_catalogue_sync_items")
    op.drop_index("ix_odoo_sync_items_postgres_entity_id", table_name="odoo_catalogue_sync_items")
    op.drop_index("ix_odoo_sync_items_odoo_record_id", table_name="odoo_catalogue_sync_items")
    op.drop_index("ix_odoo_sync_items_sync_run_id", table_name="odoo_catalogue_sync_items")
    op.drop_table("odoo_catalogue_sync_items")

    op.drop_index("ix_odoo_sync_runs_started_at", table_name="odoo_catalogue_sync_runs")
    op.drop_table("odoo_catalogue_sync_runs")
