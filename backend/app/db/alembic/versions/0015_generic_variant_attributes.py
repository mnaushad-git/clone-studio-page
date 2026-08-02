"""generic variant attributes

Retires the two hardcoded "size"/"flavor" slots that used to be the only variant
attribute concepts wired end-to-end. `catalogue_product_attribute_values` (added in
migration 0013) becomes the single source of truth for a variant's per-axis data —
read by the storefront (catalogue_query_service), checkout matching (pricing_service),
and order snapshots (order_service) alike, for any number of named axes, not just two.

Two changes:
1. `catalogue_product_variants.variant_attributes` (JSONB) is dropped. It was a
   second, disconnected representation of the same per-axis data
   `catalogue_product_attribute_values` already held — populated by the JSON-catalogue
   seed path but never by the Odoo pull-sync path, so an Odoo-originated product's
   attributes never reached the storefront even when recognized ("Size"/"Flavor").
   Dropping the second representation makes that class of bug structurally
   impossible rather than merely patched.
2. `order_items.size_label`/`order_items.flavor` (fixed String columns) are replaced
   by one `attributes_json` JSONB column — a list of
   `{"code", "name_en", "value_label_en"}` snapshots taken at order-creation time,
   matching this table's existing "denormalized, never changes after the order is
   placed" convention (already true of `sku`/`name_en`), just generalized from two
   fixed slots to an arbitrary-length list.

Existing order rows are backfilled: any non-null `size_label`/`flavor` becomes one
entry each in the new `attributes_json` array (generic `name_en` of "Size"/"Flavor",
since the real historical attribute name wasn't recorded per-order — the best
information actually available). Clean cutover, no dual-write phase: this is
pre-launch data with only test orders so far.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_items", sa.Column("attributes_json", postgresql.JSONB(), nullable=True)
    )

    order_items = sa.table(
        "order_items",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("size_label", sa.String),
        sa.column("flavor", sa.String),
        sa.column("attributes_json", postgresql.JSONB),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(order_items.c.id, order_items.c.size_label, order_items.c.flavor).where(
            sa.or_(order_items.c.size_label.is_not(None), order_items.c.flavor.is_not(None))
        )
    )
    for row in rows:
        attributes = []
        if row.size_label:
            attributes.append({"code": "size", "name_en": "Size", "value_label_en": row.size_label})
        if row.flavor:
            attributes.append(
                {"code": "flavor", "name_en": "Flavor", "value_label_en": row.flavor}
            )
        connection.execute(
            order_items.update()
            .where(order_items.c.id == row.id)
            .values(attributes_json=attributes)
        )

    op.drop_column("order_items", "size_label")
    op.drop_column("order_items", "flavor")
    op.drop_column("catalogue_product_variants", "variant_attributes")


def downgrade() -> None:
    op.add_column(
        "catalogue_product_variants", sa.Column("variant_attributes", postgresql.JSONB(), nullable=True)
    )
    op.add_column("order_items", sa.Column("size_label", sa.String(length=64), nullable=True))
    op.add_column("order_items", sa.Column("flavor", sa.String(length=64), nullable=True))

    order_items = sa.table(
        "order_items",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("size_label", sa.String),
        sa.column("flavor", sa.String),
        sa.column("attributes_json", postgresql.JSONB),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(order_items.c.id, order_items.c.attributes_json).where(
            order_items.c.attributes_json.is_not(None)
        )
    )
    for row in rows:
        by_code = {a["code"]: a["value_label_en"] for a in (row.attributes_json or [])}
        if not by_code:
            continue
        connection.execute(
            order_items.update()
            .where(order_items.c.id == row.id)
            .values(size_label=by_code.get("size"), flavor=by_code.get("flavor"))
        )

    op.drop_column("order_items", "attributes_json")
