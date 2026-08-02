"""simple product size variants

25 products that were `product_type = "simple"` (a single default variant, no real
size/flavor pricing) become `variant_parent` with a real, priced `size` attribute axis
(see `data/catalogue/products.json` — every category-default size picker on the
product page, e.g. "PACK OF 6"/"PACK OF 12", was previously a client-side-only
placeholder price that the backend could never actually charge; this makes it real,
using the exact same price math the placeholder displayed as the real, approved
price). Retires each product's old `.variant.default` row (never deleted, per this
codebase's never-delete seeding convention) the same way `0013` retired
buttercream-cake's old size-only rows: deactivated and un-defaulted so it stops being
reachable by `pricing_service.py::_select_variant` and so the new combination rows'
default doesn't collide with `uq_catalogue_product_variants_one_default_per_product`.
Re-running the catalogue seed after this migration creates the new combination rows.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_RETIRED_VARIANT_EXTERNAL_KEYS = (
    "terrific_bites.product.swiss-frosting.variant.default",
    "terrific_bites.product.moose-cream.variant.default",
    "terrific_bites.product.butter-frosting.variant.default",
    "terrific_bites.product.light-sponge.variant.default",
    "terrific_bites.product.birthday-pair.variant.default",
    "terrific_bites.product.butter-delight.variant.default",
    "terrific_bites.product.cream-cheese-donut.variant.default",
    "terrific_bites.product.whisk-whimsy.variant.default",
    "terrific_bites.product.sprinkle-1.variant.default",
    "terrific_bites.product.sprinkle-2.variant.default",
    "terrific_bites.product.sprinkle-3.variant.default",
    "terrific_bites.product.sprinkle-4.variant.default",
    "terrific_bites.product.choc-truffle.variant.default",
    "terrific_bites.product.choc-praline.variant.default",
    "terrific_bites.product.choc-ganache.variant.default",
    "terrific_bites.product.choc-caramel.variant.default",
    "terrific_bites.product.choc-mint.variant.default",
    "terrific_bites.product.choc-orange.variant.default",
    "terrific_bites.product.choc-almond.variant.default",
    "terrific_bites.product.choc-white.variant.default",
    "terrific_bites.product.choc-berry.variant.default",
    "terrific_bites.product.extra-donut.variant.default",
    "terrific_bites.product.extra-icecream.variant.default",
    "terrific_bites.product.extra-cheesecake.variant.default",
    "terrific_bites.product.extra-donuts-pair.variant.default",
)


def upgrade() -> None:
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


def downgrade() -> None:
    variants = sa.table(
        "catalogue_product_variants",
        sa.column("external_key", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
    )
    op.execute(
        variants.update()
        .where(variants.c.external_key.in_(_RETIRED_VARIANT_EXTERNAL_KEYS))
        .values(active=True, is_default=True)
    )
