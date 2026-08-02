"""Read-only access to account.tax — backs D08's VAT-mapping discovery (verification
items 2 and 9 of the phase checklist).
"""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient

MODEL = "account.tax"
FIELDS = ["id", "name", "amount", "amount_type", "type_tax_use", "price_include", "active"]


class OdooTaxRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def list_sale_taxes(
        self, *, active_only: bool = True, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        domain: list[Any] = [["type_tax_use", "=", "sale"]]
        if active_only:
            domain.append(["active", "=", True])
        page = self._client.search_read(
            MODEL, domain, FIELDS, limit=200, correlation_id=correlation_id
        )
        return page.records

    def find_by_rate(
        self, amount: float, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            MODEL,
            [["type_tax_use", "=", "sale"], ["amount", "=", amount]],
            FIELDS,
            limit=50,
            correlation_id=correlation_id,
        )
        return page.records
