"""Translation between raw Odoo JSON-RPC result shapes and the internal DTOs in
models.py. Isolated here so a protocol/version quirk (e.g. a field Odoo sometimes
omits) is fixed in one place (integration-principles.md's "isolated to
mappers.py/client.py" failure-handling guarantee).
"""

from __future__ import annotations

from typing import Any

from app.integrations.odoo.models import OdooFieldDescriptor, SearchReadPage


def parse_fields_get(raw: dict[str, dict[str, Any]]) -> dict[str, OdooFieldDescriptor]:
    """Parses a `fields_get` result (Odoo model name -> field name -> field-info
    dict) into typed descriptors, keyed by field name.
    """
    parsed: dict[str, OdooFieldDescriptor] = {}
    for name, info in raw.items():
        selection = info.get("selection")
        parsed[name] = OdooFieldDescriptor(
            name=name,
            string=info.get("string", name),
            field_type=info.get("type", "unknown"),
            required=bool(info.get("required", False)),
            readonly=bool(info.get("readonly", False)),
            relation=info.get("relation"),
            selection=[tuple(pair) for pair in selection] if selection else None,
            help=info.get("help") or None,
        )
    return parsed


def parse_search_read_page(
    records: list[dict[str, Any]], offset: int, limit: int
) -> SearchReadPage:
    return SearchReadPage(records=records, offset=offset, limit=limit)
