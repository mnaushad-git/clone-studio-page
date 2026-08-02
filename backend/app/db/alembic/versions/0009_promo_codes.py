"""promo codes

Creates promo_codes (Admin-Portal-managed) and adds order-side snapshot columns
(promo_code_id, discount_type, discount_value) so a historical order stays accurate
even if the promo is later edited or deleted. Seeds the three codes that were
previously hardcoded in app/services/checkout/pricing_service.py and mirrored in the
Storefront's legacy src/lib/store.ts PROMOS dict (WELCOME10/SWEET15/TB20) — both
hardcoded copies are removed in the same change that introduces this table, per the
task brief: "Do not silently preserve hardcoded promo logic after migration."

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
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

_DISCOUNT_TYPES = "('PERCENTAGE', 'FIXED_AMOUNT')"


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(length=16), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("minimum_order_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("maximum_discount_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per_customer_limit", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            f"discount_type IN {_DISCOUNT_TYPES}", name="ck_promo_codes_discount_type"
        ),
        sa.CheckConstraint("discount_value > 0", name="ck_promo_codes_discount_value_positive"),
        sa.CheckConstraint(
            "discount_type != 'PERCENTAGE' OR discount_value <= 100",
            name="ck_promo_codes_percentage_max_100",
        ),
        sa.CheckConstraint("minimum_order_amount >= 0", name="ck_promo_codes_minimum_order_nonneg"),
        sa.CheckConstraint("usage_count >= 0", name="ck_promo_codes_usage_count_nonneg"),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_count <= usage_limit",
            name="ck_promo_codes_usage_within_limit",
        ),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until > valid_from",
            name="ck_promo_codes_valid_until_after_from",
        ),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=True)
    op.create_index("ix_promo_codes_is_active", "promo_codes", ["is_active"])

    op.add_column(
        "orders", sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("orders", sa.Column("discount_type", sa.String(length=16), nullable=True))
    op.add_column("orders", sa.Column("discount_value", sa.Numeric(10, 2), nullable=True))
    op.create_foreign_key(
        "fk_orders_promo_code_id",
        "orders",
        "promo_codes",
        ["promo_code_id"],
        ["id"],
        ondelete="SET NULL",
    )

    promo_codes_table = sa.table(
        "promo_codes",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
        sa.column("discount_type", sa.String),
        sa.column("discount_value", sa.Numeric),
        sa.column("minimum_order_amount", sa.Numeric),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        promo_codes_table,
        [
            {
                "id": uuid.uuid4(),
                "code": "WELCOME10",
                "description": "10% off — migrated from the previous hardcoded promo list.",
                "discount_type": "PERCENTAGE",
                "discount_value": 10,
                "minimum_order_amount": 0,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "code": "SWEET15",
                "description": "15% off orders over SAR 100 — migrated from the previous "
                "hardcoded promo list.",
                "discount_type": "PERCENTAGE",
                "discount_value": 15,
                "minimum_order_amount": 100,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "code": "TB20",
                "description": "20% off orders over SAR 200 — migrated from the previous "
                "hardcoded promo list.",
                "discount_type": "PERCENTAGE",
                "discount_value": 20,
                "minimum_order_amount": 200,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_promo_code_id", "orders", type_="foreignkey")
    op.drop_column("orders", "discount_value")
    op.drop_column("orders", "discount_type")
    op.drop_column("orders", "promo_code_id")

    op.drop_index("ix_promo_codes_is_active", table_name="promo_codes")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")
