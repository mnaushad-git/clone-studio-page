"""Read-only access to product.pricelist / product.pricelist.item — backs the
tax-inclusive/exclusive and default-pricelist verification items (D08, checklist
item 10).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.integrations.odoo.client import OdooClient

PRICELIST_MODEL = "product.pricelist"
PRICELIST_FIELDS = ["id", "name", "currency_id", "active"]
PRICELIST_ITEM_MODEL = "product.pricelist.item"
PRICELIST_ITEM_FIELDS = [
    "id",
    "pricelist_id",
    "product_tmpl_id",
    "product_id",
    "fixed_price",
    "compute_price",
    "write_date",
]


class OdooPricelistRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def list_active_pricelists(self, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        page = self._client.search_read(
            PRICELIST_MODEL,
            [["active", "=", True]],
            PRICELIST_FIELDS,
            limit=100,
            correlation_id=correlation_id,
        )
        return page.records

    def iter_items_for_pricelist(
        self,
        pricelist_id: int,
        *,
        domain: list[Any] | None = None,
        max_records: int,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Pull-sync source for per-product pricelist overrides. Only `fixed_price`
        items are meaningful to this sync — formula/percentage-discount pricelist
        rules (`compute_price != "fixed"`) are read but left for the caller to skip,
        since resolving a full pricing formula is out of scope here.
        """
        base: list[Any] = [["pricelist_id", "=", pricelist_id]]
        yield from self._client.iter_search_read(
            PRICELIST_ITEM_MODEL,
            base + (domain or []),
            PRICELIST_ITEM_FIELDS,
            max_records=max_records,
            correlation_id=correlation_id,
        )
