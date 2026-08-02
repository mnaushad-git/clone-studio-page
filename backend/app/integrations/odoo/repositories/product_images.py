"""Read-only access to product.image — the gallery-image source for the Odoo ->
PostgreSQL pull sync. The PRIMARY-role image is never read here: it comes from
product.template.image_1920 (already fetched by OdooProductRepository.iter_all_templates),
so this repository only ever backs GALLERY images.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.integrations.odoo.client import OdooClient

MODEL = "product.image"
FIELDS = [
    "id",
    "name",
    "product_tmpl_id",
    "product_variant_id",
    "sequence",
    "image_1920",
    "write_date",
]

# Each record here carries a base64 image payload — a default-sized page (200 rows)
# would be a multi-megabyte single JSON-RPC response, so this repository pages in much
# smaller batches than the rest of the Odoo integration.
_IMAGE_BATCH_SIZE = 20


class OdooProductImageRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def iter_for_templates(
        self,
        template_ids: list[int],
        *,
        max_records: int,
        batch_size: int = _IMAGE_BATCH_SIZE,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        if not template_ids:
            return
        yield from self._client.iter_search_read(
            MODEL,
            [["product_tmpl_id", "in", template_ids]],
            FIELDS,
            order="product_tmpl_id, sequence",
            batch_size=batch_size,
            max_records=max_records,
            correlation_id=correlation_id,
        )
