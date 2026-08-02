"""Read-only access to res.currency — backs D07's SAR-currency confirmation."""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient

MODEL = "res.currency"
FIELDS = ["id", "name", "symbol", "active"]


class OdooCurrencyRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def find_by_code(
        self, iso_code: str, *, correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        page = self._client.search_read(
            MODEL, [["name", "=", iso_code]], FIELDS, limit=5, correlation_id=correlation_id
        )
        return page.records
