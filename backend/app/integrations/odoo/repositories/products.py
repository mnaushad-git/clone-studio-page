"""Read-only access to product.template / product.product — backs SKU-conflict
detection and the product field-mapping evidence gathering.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.integrations.odoo.client import OdooClient

TEMPLATE_MODEL = "product.template"
VARIANT_MODEL = "product.product"

TEMPLATE_FIELDS = [
    "id",
    "name",
    "display_name",
    "default_code",
    "categ_id",
    "list_price",
    "currency_id",
    "taxes_id",
    "active",
    "sale_ok",
    "type",
    "uom_id",
    "description_sale",
    "image_1920",
]
VARIANT_FIELDS = ["id", "name", "default_code", "product_tmpl_id", "active"]

# write_date is only needed for the incremental pull sync's checkpoint filtering, not
# for the conflict-check/matching-evidence methods below — kept as separate constants
# so those existing callers' field lists (and any recorded audit payloads) are unaffected.
# product_template_attribute_value_ids likewise: only the pull sync needs it (to
# resolve which attribute-value combination each variant represents), so it's added
# only to the _SYNC_FIELDS superset, not the conflict-check VARIANT_FIELDS.
TEMPLATE_SYNC_FIELDS = [*TEMPLATE_FIELDS, "write_date"]
VARIANT_SYNC_FIELDS = [*VARIANT_FIELDS, "write_date", "product_template_attribute_value_ids"]

# A conflict/name lookup never needs more than a handful of matches to prove a
# collision exists; this bounds every method here without requiring callers to
# think about pagination for what is, by design, a narrow point lookup.
_LOOKUP_LIMIT = 50


class OdooProductRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def find_templates_by_default_code(
        self, default_code: str, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            TEMPLATE_MODEL,
            [["default_code", "=", default_code]],
            TEMPLATE_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def find_variants_by_default_code(
        self, default_code: str, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            VARIANT_MODEL,
            [["default_code", "=", default_code]],
            VARIANT_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def find_templates_by_name(
        self, name: str, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            TEMPLATE_MODEL,
            [["name", "=", name]],
            TEMPLATE_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def iter_all_templates(
        self,
        *,
        domain: list[Any] | None = None,
        max_records: int,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Bounded full-catalogue sweep — used by product reconciliation-style
        discovery (no domain, TEMPLATE_FIELDS) and by the Odoo -> PostgreSQL pull sync
        (optional incremental `write_date >=` domain, TEMPLATE_SYNC_FIELDS). `max_records`
        is required (see client.iter_search_read).
        """
        yield from self._client.iter_search_read(
            TEMPLATE_MODEL,
            domain or [],
            TEMPLATE_SYNC_FIELDS if domain is not None else TEMPLATE_FIELDS,
            max_records=max_records,
            correlation_id=correlation_id,
        )

    def iter_all_variants(
        self,
        *,
        domain: list[Any] | None = None,
        max_records: int,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Bounded full-catalogue sweep over product.product — the pull sync's variant
        source. Every Odoo product (even one with no genuine variation) has at least
        one product.product row per template, which is what backs this app's "every
        product has at least one variant" invariant.
        """
        yield from self._client.iter_search_read(
            VARIANT_MODEL,
            domain or [],
            VARIANT_SYNC_FIELDS,
            order="product_tmpl_id",
            max_records=max_records,
            correlation_id=correlation_id,
        )
