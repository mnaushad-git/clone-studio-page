"""catalogue foundation

Creates the PostgreSQL catalogue domain: categories, products, variants, prices,
availability, images, merchandising, storefront sections, moments, recipients,
their product mappings, product recommendations, and sync/seed-run metadata.
Phase 3 (docs/architecture/target-architecture.md, docs/catalogue/final-data-ownership.md).

No Odoo client, no catalogue APIs, no cart/order/customer tables — see CLAUDE.md
Phase 3 scope boundaries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Shared column groups, mirroring app/models/mixins.py so the migration and the ORM
# models describe the same shape.
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


def _source_sync_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("source_system", sa.String(length=50), nullable=False, server_default="seed"),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def upgrade() -> None:
    # 1. catalogue_categories --------------------------------------------------------
    op.create_table(
        "catalogue_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("odoo_category_id", sa.Integer(), nullable=True),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["parent_id"], ["catalogue_categories.id"]),
        sa.UniqueConstraint("external_key", name="uq_catalogue_categories_external_key"),
        sa.UniqueConstraint("code", name="uq_catalogue_categories_code"),
        sa.UniqueConstraint("slug", name="uq_catalogue_categories_slug"),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_catalogue_categories_display_order_nonneg"
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id != id", name="ck_catalogue_categories_no_self_parent"
        ),
    )
    op.create_index("ix_catalogue_categories_active", "catalogue_categories", ["active"])
    op.create_index("ix_catalogue_categories_parent_id", "catalogue_categories", ["parent_id"])
    op.create_index(
        "ix_catalogue_categories_odoo_category_id", "catalogue_categories", ["odoo_category_id"]
    )

    # 2. catalogue_products -----------------------------------------------------------
    op.create_table(
        "catalogue_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("short_description_en", sa.String(length=500), nullable=True),
        sa.Column("short_description_ar", sa.String(length=500), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_type", sa.String(length=20), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=50), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sellable", sa.Boolean(), nullable=False),
        sa.Column("odoo_product_template_id", sa.Integer(), nullable=True),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["category_id"], ["catalogue_categories.id"]),
        sa.UniqueConstraint("external_key", name="uq_catalogue_products_external_key"),
        sa.UniqueConstraint("sku", name="uq_catalogue_products_sku"),
        sa.UniqueConstraint("slug", name="uq_catalogue_products_slug"),
        sa.CheckConstraint(
            "product_type IN ('simple', 'variant_parent')",
            name="ck_catalogue_products_product_type",
        ),
        sa.CheckConstraint(
            "source_system IN ('seed', 'odoo', 'admin')",
            name="ck_catalogue_products_source_system",
        ),
    )
    op.create_index("ix_catalogue_products_category_id", "catalogue_products", ["category_id"])
    op.create_index("ix_catalogue_products_active", "catalogue_products", ["active"])
    op.create_index("ix_catalogue_products_sellable", "catalogue_products", ["sellable"])
    op.create_index(
        "ix_catalogue_products_odoo_product_template_id",
        "catalogue_products",
        ["odoo_product_template_id"],
    )
    op.create_index("ix_catalogue_products_name_en", "catalogue_products", ["name_en"])

    # 3. catalogue_product_variants ----------------------------------------------------
    op.create_table(
        "catalogue_product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("variant_attributes", postgresql.JSONB(), nullable=True),
        sa.Column("odoo_product_variant_id", sa.Integer(), nullable=True),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.UniqueConstraint("external_key", name="uq_catalogue_product_variants_external_key"),
        sa.UniqueConstraint("sku", name="uq_catalogue_product_variants_sku"),
    )
    op.create_index(
        "ix_catalogue_product_variants_product_id", "catalogue_product_variants", ["product_id"]
    )
    op.create_index(
        "uq_catalogue_product_variants_one_default_per_product",
        "catalogue_product_variants",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    # 4. catalogue_product_prices -------------------------------------------------------
    op.create_table(
        "catalogue_product_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_reference", sa.String(length=255), nullable=True),
        sa.Column("price_includes_tax", sa.Boolean(), nullable=True),
        sa.Column(
            "valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("odoo_pricelist_id", sa.Integer(), nullable=True),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_variant_id"], ["catalogue_product_variants.id"]),
        sa.CheckConstraint("amount >= 0", name="ck_catalogue_product_prices_amount_nonneg"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_catalogue_product_prices_valid_range",
        ),
    )
    op.create_index(
        "ix_catalogue_product_prices_variant_id", "catalogue_product_prices", ["product_variant_id"]
    )
    op.create_index(
        "uq_catalogue_product_prices_one_active_per_variant_currency",
        "catalogue_product_prices",
        ["product_variant_id", "currency"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    # 5. catalogue_product_availability -------------------------------------------------
    op.create_table(
        "catalogue_product_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("availability_status", sa.String(length=20), nullable=False),
        sa.Column("quantity_available", sa.Integer(), nullable=True),
        sa.Column("allow_backorder", sa.Boolean(), nullable=False),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_variant_id"], ["catalogue_product_variants.id"]),
        sa.UniqueConstraint(
            "product_variant_id", name="uq_catalogue_product_availability_variant_id"
        ),
        sa.CheckConstraint(
            "availability_status IN "
            "('UNKNOWN', 'AVAILABLE', 'OUT_OF_STOCK', 'DISCONTINUED', 'PREORDER')",
            name="ck_catalogue_product_availability_status",
        ),
        sa.CheckConstraint(
            "quantity_available IS NULL OR quantity_available >= 0",
            name="ck_catalogue_product_availability_quantity_nonneg",
        ),
    )

    # 6. catalogue_product_images ---------------------------------------------------------
    op.create_table(
        "catalogue_product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_role", sa.String(length=30), nullable=False),
        sa.Column("original_path", sa.String(length=1000), nullable=False),
        sa.Column("storage_url", sa.String(length=1000), nullable=True),
        sa.Column("alt_text_en", sa.String(length=500), nullable=True),
        sa.Column("alt_text_ar", sa.String(length=500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        *_source_sync_columns(),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.ForeignKeyConstraint(["product_variant_id"], ["catalogue_product_variants.id"]),
        sa.CheckConstraint(
            "image_role IN ('PRIMARY', 'GALLERY', 'STOREFRONT_OVERRIDE', 'MOBILE_OVERRIDE')",
            name="ck_catalogue_product_images_role",
        ),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_images_display_order_nonneg"
        ),
    )
    op.create_index(
        "ix_catalogue_product_images_product_id", "catalogue_product_images", ["product_id"]
    )
    op.create_index(
        "ix_catalogue_product_images_variant_id",
        "catalogue_product_images",
        ["product_variant_id"],
    )

    # 7. catalogue_product_merchandising -----------------------------------------------
    op.create_table(
        "catalogue_product_merchandising",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storefront_visible", sa.Boolean(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("is_new", sa.Boolean(), nullable=False),
        sa.Column("is_bestseller", sa.Boolean(), nullable=True),
        sa.Column("badge_en", sa.String(length=100), nullable=True),
        sa.Column("badge_ar", sa.String(length=100), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("marketing_title_en", sa.String(length=255), nullable=True),
        sa.Column("marketing_title_ar", sa.String(length=255), nullable=True),
        sa.Column("marketing_description_en", sa.Text(), nullable=True),
        sa.Column("marketing_description_ar", sa.Text(), nullable=True),
        sa.Column("seo_title_en", sa.String(length=255), nullable=True),
        sa.Column("seo_title_ar", sa.String(length=255), nullable=True),
        sa.Column("seo_description_en", sa.Text(), nullable=True),
        sa.Column("seo_description_ar", sa.Text(), nullable=True),
        sa.Column("storefront_image_override_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mobile_image_override_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.ForeignKeyConstraint(["storefront_image_override_id"], ["catalogue_product_images.id"]),
        sa.ForeignKeyConstraint(["mobile_image_override_id"], ["catalogue_product_images.id"]),
        sa.UniqueConstraint("product_id", name="uq_catalogue_product_merchandising_product_id"),
    )

    # 8. storefront_sections --------------------------------------------------------------
    op.create_table(
        "storefront_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.UniqueConstraint("external_key", name="uq_storefront_sections_external_key"),
        sa.UniqueConstraint("code", name="uq_storefront_sections_code"),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_storefront_sections_display_order_nonneg"
        ),
    )
    op.create_index("ix_storefront_sections_active", "storefront_sections", ["active"])

    # 9. storefront_section_products -------------------------------------------------------
    op.create_table(
        "storefront_section_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["section_id"], ["storefront_sections.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.UniqueConstraint(
            "section_id", "product_id", name="uq_storefront_section_products_section_product"
        ),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_storefront_section_products_display_order_nonneg"
        ),
    )

    # 10. catalogue_moments ------------------------------------------------------------------
    op.create_table(
        "catalogue_moments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.UniqueConstraint("external_key", name="uq_catalogue_moments_external_key"),
        sa.UniqueConstraint("code", name="uq_catalogue_moments_code"),
        sa.UniqueConstraint("slug", name="uq_catalogue_moments_slug"),
        sa.CheckConstraint("display_order >= 0", name="ck_catalogue_moments_display_order_nonneg"),
    )
    op.create_index("ix_catalogue_moments_active", "catalogue_moments", ["active"])

    # 11. catalogue_recipients ---------------------------------------------------------------
    op.create_table(
        "catalogue_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.UniqueConstraint("external_key", name="uq_catalogue_recipients_external_key"),
        sa.UniqueConstraint("code", name="uq_catalogue_recipients_code"),
        sa.UniqueConstraint("slug", name="uq_catalogue_recipients_slug"),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_catalogue_recipients_display_order_nonneg"
        ),
    )
    op.create_index("ix_catalogue_recipients_active", "catalogue_recipients", ["active"])

    # 12. catalogue_product_moments -----------------------------------------------------------
    op.create_table(
        "catalogue_product_moments",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("moment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.ForeignKeyConstraint(["moment_id"], ["catalogue_moments.id"]),
        sa.PrimaryKeyConstraint("product_id", "moment_id"),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_moments_display_order_nonneg"
        ),
    )

    # 13. catalogue_product_recipients --------------------------------------------------------
    op.create_table(
        "catalogue_product_recipients",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["catalogue_recipients.id"]),
        sa.PrimaryKeyConstraint("product_id", "recipient_id"),
        sa.CheckConstraint(
            "display_order >= 0", name="ck_catalogue_product_recipients_display_order_nonneg"
        ),
    )

    # 14. catalogue_product_recommendations ---------------------------------------------------
    op.create_table(
        "catalogue_product_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommended_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_type", sa.String(length=30), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_TIMESTAMP_COLUMNS,
        sa.ForeignKeyConstraint(["product_id"], ["catalogue_products.id"]),
        sa.ForeignKeyConstraint(["recommended_product_id"], ["catalogue_products.id"]),
        sa.UniqueConstraint(
            "product_id",
            "recommended_product_id",
            "recommendation_type",
            name="uq_catalogue_product_recommendations_unique_triplet",
        ),
        sa.CheckConstraint(
            "product_id != recommended_product_id",
            name="ck_catalogue_product_recommendations_no_self_recommend",
        ),
        sa.CheckConstraint(
            "recommendation_type IN ('MANUAL', 'SAME_CATEGORY', 'FREQUENTLY_BOUGHT')",
            name="ck_catalogue_product_recommendations_type",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_catalogue_product_recommendations_display_order_nonneg",
        ),
    )
    op.create_index(
        "ix_catalogue_product_recommendations_product_id",
        "catalogue_product_recommendations",
        ["product_id"],
    )

    # 15. integration_sync_checkpoints -------------------------------------------------------
    op.create_table(
        "integration_sync_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("integration_name", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("checkpoint_value", sa.String(length=255), nullable=True),
        sa.Column("last_successful_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        *_TIMESTAMP_COLUMNS,
        sa.UniqueConstraint(
            "integration_name",
            "entity_type",
            name="uq_integration_sync_checkpoints_name_entity",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')",
            name="ck_integration_sync_checkpoints_status",
        ),
    )

    # 16. catalogue_seed_runs -----------------------------------------------------------------
    op.create_table(
        "catalogue_seed_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("seed_version", sa.String(length=50), nullable=False),
        sa.Column("source_checksum", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCESS', 'FAILED', 'DRY_RUN')",
            name="ck_catalogue_seed_runs_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("catalogue_seed_runs")
    op.drop_table("integration_sync_checkpoints")
    op.drop_table("catalogue_product_recommendations")
    op.drop_table("catalogue_product_recipients")
    op.drop_table("catalogue_product_moments")
    op.drop_table("catalogue_recipients")
    op.drop_table("catalogue_moments")
    op.drop_table("storefront_section_products")
    op.drop_table("storefront_sections")
    op.drop_table("catalogue_product_merchandising")
    op.drop_table("catalogue_product_images")
    op.drop_table("catalogue_product_availability")
    op.drop_table("catalogue_product_prices")
    op.drop_table("catalogue_product_variants")
    op.drop_table("catalogue_products")
    op.drop_table("catalogue_categories")
