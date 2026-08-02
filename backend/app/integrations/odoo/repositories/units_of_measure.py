"""Read-only access to uom.uom — backs D09's Unit-of-Measure discovery."""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient

MODEL = "uom.uom"
FIELDS = ["id", "name", "category_id", "uom_type", "active"]


class OdooUomRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def list_reference_units(self, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        """Units whose `uom_type` is `reference` — the natural "Unit"/"Each" default
        for a per-item bakery product (odoo-configuration-checklist.md D09).
        """
        page = self._client.search_read(
            MODEL,
            [["uom_type", "=", "reference"]],
            FIELDS,
            limit=100,
            correlation_id=correlation_id,
        )
        return page.records

    def find_by_name(self, name: str, *, correlation_id: str | None = None) -> list[dict[str, Any]]:
        page = self._client.search_read(
            MODEL, [["name", "=", name]], FIELDS, limit=50, correlation_id=correlation_id
        )
        return page.records
