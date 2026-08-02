from __future__ import annotations

from app.integrations.odoo.discovery.catalogue_mapping import (
    Evidence,
    MappingClassification,
    build_category_mapping,
    build_product_mapping,
)
from app.integrations.odoo.models import OdooFieldDescriptor


def _field(name: str, field_type: str = "char") -> OdooFieldDescriptor:
    return OdooFieldDescriptor(
        name=name, string=name, field_type=field_type, required=False, readonly=False
    )


def test_category_mapping_without_discovery_is_unverified_assumption() -> None:
    mapping = build_category_mapping(None)

    name_en = next(m for m in mapping if m.canonical_field == "name_en")
    assert name_en.evidence == Evidence.UNVERIFIED_ASSUMPTION
    assert name_en.odoo_model == "product.category"
    assert name_en.odoo_field == "name"


def test_category_mapping_confirms_field_present_on_live_instance() -> None:
    fields_by_model = {
        "product.category": {"name": _field("name"), "active": _field("active", "boolean")}
    }

    mapping = build_category_mapping(fields_by_model)

    name_en = next(m for m in mapping if m.canonical_field == "name_en")
    assert name_en.classification == MappingClassification.STANDARD_FIELD_CONFIRMED
    assert name_en.evidence == Evidence.VERIFIED_FACT


def test_category_mapping_marks_not_supported_when_model_missing() -> None:
    mapping = build_category_mapping({"product.category": None})

    name_en = next(m for m in mapping if m.canonical_field == "name_en")
    assert name_en.classification == MappingClassification.NOT_SUPPORTED
    assert name_en.evidence == Evidence.VERIFIED_FACT


def test_category_mapping_display_order_is_postgresql_only() -> None:
    mapping = build_category_mapping(None)

    display_order = next(m for m in mapping if m.canonical_field == "display order")
    assert display_order.classification == MappingClassification.POSTGRESQL_ONLY
    assert display_order.odoo_model is None


def test_product_mapping_sku_targets_variant_default_code() -> None:
    mapping = build_product_mapping(None)

    sku = next(m for m in mapping if m.canonical_field == "sku")
    assert sku.odoo_model == "product.product"
    assert sku.odoo_field == "default_code"


def test_product_mapping_marks_field_absent_when_not_found_on_live_instance() -> None:
    fields_by_model = {
        "product.template": {"name": _field("name")}
    }  # no default_code, no list_price, etc.

    mapping = build_product_mapping(fields_by_model)

    base_price = next(m for m in mapping if m.canonical_field == "base sales price")
    assert base_price.classification == MappingClassification.NOT_SUPPORTED
    assert base_price.evidence == Evidence.VERIFIED_FACT


def test_product_mapping_external_key_requires_odoo_configuration() -> None:
    mapping = build_product_mapping(None)

    external_key = next(m for m in mapping if m.canonical_field == "external_key")
    assert external_key.classification == MappingClassification.REQUIRES_ODOO_CONFIGURATION
    assert external_key.odoo_model == "ir.model.data"


def test_product_mapping_slug_and_short_description_are_postgresql_only() -> None:
    mapping = build_product_mapping(None)

    classifications = {m.canonical_field: m.classification for m in mapping}
    assert classifications["slug"] == MappingClassification.POSTGRESQL_ONLY
    assert classifications["short description"] == MappingClassification.POSTGRESQL_ONLY
