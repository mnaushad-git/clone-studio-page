"""Bounded, read-only field discovery across the models the catalogue integration
cares about ("Read-only model discovery" in the phase brief).
"""

from __future__ import annotations

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooIntegrationError
from app.integrations.odoo.models import OdooFieldDescriptor

# Every model the phase brief names under "Read-only model discovery". Not every
# model is guaranteed installed — model_availability (repositories/metadata.py)
# is checked first by discovery/capabilities.py; this module fetches fields only for
# models known to exist, and records "not installed" for the rest rather than raising.
CATALOGUE_RELEVANT_MODELS = [
    "product.template",
    "product.product",
    "product.category",
    "account.tax",
    "uom.uom",
    "res.currency",
    "product.pricelist",
    "product.pricelist.item",
    "stock.quant",
    "stock.warehouse",
    "res.company",
    "product.image",
]


def discover_fields_for_models(
    client: OdooClient,
    models: list[str],
    *,
    correlation_id: str | None = None,
) -> dict[str, dict[str, OdooFieldDescriptor] | None]:
    """Returns model -> {field_name: descriptor}, or model -> None if fields_get
    itself failed (model not installed, or no access) — callers distinguish "no
    fields because unavailable" from "field X specifically absent" this way.
    """
    result: dict[str, dict[str, OdooFieldDescriptor] | None] = {}
    for model in models:
        try:
            result[model] = client.fields_get(model, correlation_id=correlation_id)
        except OdooIntegrationError:
            result[model] = None
    return result
