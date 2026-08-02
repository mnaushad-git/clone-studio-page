"""Read-only access to stock.quant / stock.warehouse — backs the opening-inventory
(D19) and stock/availability-query-strategy verification items.
"""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient

WAREHOUSE_MODEL = "stock.warehouse"
WAREHOUSE_FIELDS = ["id", "name", "code", "company_id"]
QUANT_MODEL = "stock.quant"


class OdooStockRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def list_warehouses(self, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        page = self._client.search_read(
            WAREHOUSE_MODEL, [], WAREHOUSE_FIELDS, limit=50, correlation_id=correlation_id
        )
        return page.records

    def get_available_quantities(
        self,
        product_ids: list[int],
        *,
        location_id: int | None = None,
        correlation_id: str | None = None,
    ) -> dict[int, float]:
        """Returns {product.product id: quantity - reserved_quantity}, summed across
        matching locations. `location_id=None` sums every internal-usage location
        (a reasonable default when no specific storefront-facing warehouse/location has
        been configured). Raises OdooIntegrationError (e.g. when the Inventory app
        isn't installed and stock.quant reports "model not installed") — the caller is
        responsible for catching this and degrading gracefully rather than failing the
        whole catalogue sync, since this is a real, documented gap in the connected
        Odoo environment (see docs/integrations/odoo-operations-runbook.md).
        """
        if not product_ids:
            return {}
        domain: list[Any] = [["product_id", "in", product_ids]]
        domain.append(
            ["location_id", "=", location_id]
            if location_id is not None
            else ["location_id.usage", "=", "internal"]
        )
        groups = self._client.execute_readonly(
            QUANT_MODEL,
            "read_group",
            [domain, ["quantity:sum", "reserved_quantity:sum"], ["product_id"]],
            {},
            correlation_id=correlation_id,
        )
        return {
            g["product_id"][0]: float(g.get("quantity") or 0)
            - float(g.get("reserved_quantity") or 0)
            for g in groups
        }
