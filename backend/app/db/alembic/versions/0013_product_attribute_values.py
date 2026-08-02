"""product attribute values

Adds `catalogue_product_attribute_values` — the join between a
`catalogue_product_variants` row and the specific Odoo `product.attribute`/
`product.attribute.value` identity it carries (size axis, flavor axis, etc.). This is
additive to the existing `variant_attributes` JSONB (storefront-display shape, untouched)
and is what the Odoo variant-modeling importer adopts `odoo_attribute_id`/
`odoo_attribute_value_id` into.

Also retires buttercream-cake's two size-only variant rows
(`terrific_bites.product.buttercream-cake.variant.6-inch` / `.9-inch`): flavor becomes a
real combinatorial axis (see `seed_service.py`/`data/catalogue/products.json`), so the
seed now produces 4 size*flavor combination rows with new external_keys instead. The old
2 rows are deactivated and un-defaulted here (never deleted, per this codebase's
never-delete seeding convention) so they stop being reachable by
`pricing_service.py::_select_variant` (which already filters to `active` variants) and so
the new default row doesn't collide with
`uq_catalogue_product_variants_one_default_per_product` (a partial unique index on
`is_default` that isn't itself scoped by `active`). Re-running the catalogue seed after
this migration creates the 4 new combination rows.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_RETIRED_VARIANT_EXTERNAL_KEYS = (
    "terrific_bites.product.buttercream-cake.variant.6-inch",
    "terrific_bites.product.buttercream-cake.variant.9-inch",
)


def upgrade() -> None:
    op.create_table(
        "catalogue_product_attribute_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribute_code", sa.String(length=50), nullable=False),
        sa.Column("attribute_name_en", sa.String(length=255), nullable=False),
        sa.Column("value_label_en", sa.String(length=255), nullable=False),
        sa.Column("odoo_attribute_id", sa.Integer(), nullable=True),
        sa.Column("odoo_attribute_value_id", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["variant_id"], ["catalogue_product_variants.id"]),
    )
    op.create_index(
        "ix_catalogue_product_attribute_values_variant_id",
        "catalogue_product_attribute_values",
        ["variant_id"],
    )
    op.create_index(
        "ix_catalogue_product_attribute_values_attribute_name_en",
        "catalogue_product_attribute_values",
        ["attribute_name_en"],
    )
    op.create_index(
        "uq_catalogue_product_attribute_values_variant_axis",
        "catalogue_product_attribute_values",
        ["variant_id", "attribute_code"],
        unique=True,
    )

    variants = sa.table(
        "catalogue_product_variants",
        sa.column("external_key", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
    )
    op.execute(
        variants.update()
        .where(variants.c.external_key.in_(_RETIRED_VARIANT_EXTERNAL_KEYS))
        .values(active=False, is_default=False)
    )

    # odoo_catalogue_import_items.entity_type's check constraint predates this feature —
    # widen it to admit the two new plan-item kinds this importer now produces.
    op.drop_constraint(
        "ck_odoo_import_items_entity_type", "odoo_catalogue_import_items", type_="check"
    )
    op.create_check_constraint(
        "ck_odoo_import_items_entity_type",
        "odoo_catalogue_import_items",
        "entity_type IN ('CATEGORY', 'PRODUCT_TEMPLATE', 'PRODUCT_VARIANT', 'PRODUCT_IMAGE', "
        "'EXTERNAL_XML_ID', 'PRODUCT_ATTRIBUTE', 'PRODUCT_ATTRIBUTE_VALUE')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_odoo_import_items_entity_type", "odoo_catalogue_import_items", type_="check"
    )
    op.create_check_constraint(
        "ck_odoo_import_items_entity_type",
        "odoo_catalogue_import_items",
        "entity_type IN ('CATEGORY', 'PRODUCT_TEMPLATE', 'PRODUCT_VARIANT', 'PRODUCT_IMAGE', "
        "'EXTERNAL_XML_ID')",
    )


    variants = sa.table(
        "catalogue_product_variants",
        sa.column("external_key", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
    )
    # Original state: 6-inch had delta 0 (is_default=True), 9-inch delta 80 (False) — see
    # seed_service.py's `is_default = size.get("delta", 0) == 0` at the time these rows
    # were first seeded.
    op.execute(
        variants.update()
        .where(variants.c.external_key == "terrific_bites.product.buttercream-cake.variant.6-inch")
        .values(active=True, is_default=True)
    )
    op.execute(
        variants.update()
        .where(variants.c.external_key == "terrific_bites.product.buttercream-cake.variant.9-inch")
        .values(active=True, is_default=False)
    )

    op.drop_index(
        "uq_catalogue_product_attribute_values_variant_axis",
        table_name="catalogue_product_attribute_values",
    )
    op.drop_index(
        "ix_catalogue_product_attribute_values_attribute_name_en",
        table_name="catalogue_product_attribute_values",
    )
    op.drop_index(
        "ix_catalogue_product_attribute_values_variant_id",
        table_name="catalogue_product_attribute_values",
    )
    op.drop_table("catalogue_product_attribute_values")
