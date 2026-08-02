"""Read-only access to product.category — backs catalogue conflict detection and the
category field-mapping evidence gathering.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.integrations.odoo.client import OdooClient

MODEL = "product.category"
DEFAULT_FIELDS = ["id", "name", "display_name", "parent_id", "complete_name"]
SYNC_FIELDS = [*DEFAULT_FIELDS, "write_date"]

# Import-conflict checks fetch by exact name — a full-table scan is never needed for
# this repository's methods, so no max_records-bounded iteration is exposed here.
_CONFLICT_CHECK_LIMIT = 50


class OdooCategoryRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def find_by_name(
        self, name: str, *, correlation_id: str | None = None
    ) -> list[dict[str, object]]:
        page = self._client.search_read(
            MODEL,
            [["name", "=", name]],
            DEFAULT_FIELDS,
            limit=_CONFLICT_CHECK_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def find_terrific_bites_categories(
        self, *, correlation_id: str | None = None
    ) -> list[dict[str, object]]:
        """Looks for any existing category that already looks like ours — a coarse
        `ilike` sweep, not an external-id lookup (external ids aren't created in this
        phase), used purely to answer verification item 24 ("does an existing
        Terrific Bites category already exist").
        """
        page = self._client.search_read(
            MODEL,
            [["name", "ilike", "terrific"]],
            DEFAULT_FIELDS,
            limit=_CONFLICT_CHECK_LIMIT,
            correlation_id=correlation_id,
        )
        return page.records

    def iter_all_categories(
        self,
        *,
        domain: list[Any] | None = None,
        max_records: int,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Bounded full-catalogue sweep for the Odoo -> PostgreSQL pull sync. `domain`
        lets the caller scope this to an incremental `write_date >=` window; an empty/
        None domain sweeps every category. `max_records` is required (see
        client.iter_search_read).
        """
        yield from self._client.iter_search_read(
            MODEL,
            domain or [],
            SYNC_FIELDS,
            order="id",
            max_records=max_records,
            correlation_id=correlation_id,
        )
