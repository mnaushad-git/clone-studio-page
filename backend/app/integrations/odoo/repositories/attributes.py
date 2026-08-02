"""Read-only access to product.attribute / product.attribute.value / product.template.
attribute.line — backs the variant-attribute matching pass (plan_attributes/
plan_variants) so a shared attribute like "Flavor" is matched by name before ever being
created, never duplicated across products.
"""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient

ATTRIBUTE_MODEL = "product.attribute"
VALUE_MODEL = "product.attribute.value"
TEMPLATE_LINE_MODEL = "product.template.attribute.line"
TEMPLATE_VALUE_MODEL = "product.template.attribute.value"

ATTRIBUTE_FIELDS = ["id", "name", "create_variant"]
VALUE_FIELDS = ["id", "name", "attribute_id"]
TEMPLATE_LINE_FIELDS = ["id", "attribute_id", "value_ids", "product_tmpl_id"]
TEMPLATE_VALUE_FIELDS = ["id", "product_attribute_value_id", "price_extra"]

# A name/scope lookup never needs more than a handful of matches to prove a collision
# exists or find the one real match — this bounds every method here without requiring
# callers to think about pagination for what is, by design, a narrow point lookup.
_LOOKUP_LIMIT = 50


class OdooAttributeRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def find_attribute_by_name(
        self, name: str, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            ATTRIBUTE_MODEL,
            [["name", "=", name]],
            ATTRIBUTE_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def find_value_by_name_and_attribute(
        self, name: str, attribute_id: int, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            VALUE_MODEL,
            [["name", "=", name], ["attribute_id", "=", attribute_id]],
            VALUE_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def find_template_attribute_line(
        self, template_id: int, attribute_id: int, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            TEMPLATE_LINE_MODEL,
            [["product_tmpl_id", "=", template_id], ["attribute_id", "=", attribute_id]],
            TEMPLATE_LINE_FIELDS,
            limit=_LOOKUP_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    # -- bulk id-list reads (pull-sync sweep pattern, not a point lookup) -----------

    def read_template_attribute_values(
        self, ids: list[int], *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """product.template.attribute.value rows — the per-template-per-value join
        that carries price_extra and points at the underlying product.attribute.value
        (via product_attribute_value_id). Bulk `read()`, not `search_read()`: the pull
        sync already knows exactly which ids it needs (from each variant's
        product_template_attribute_value_ids), unlike the push side's narrow
        name/scope lookups above.
        """
        if not ids:
            return []
        return self._client.read(
            TEMPLATE_VALUE_MODEL, ids, TEMPLATE_VALUE_FIELDS, correlation_id=correlation_id
        )

    def read_attribute_values(
        self, ids: list[int], *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """product.attribute.value rows — name + parent attribute_id, for a known set
        of ids (see read_template_attribute_values's docstring)."""
        if not ids:
            return []
        return self._client.read(VALUE_MODEL, ids, VALUE_FIELDS, correlation_id=correlation_id)
