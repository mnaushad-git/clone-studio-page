"""Evidence-based canonical-field-to-Odoo-field mapping.

Produces the mapping table the phase brief asks for: one row per canonical
Category/Product field, classified per the enum below, with an explicit evidence
level so a reader can tell a verified fact apart from an inferred mapping or an
unverified assumption carried over from docs/catalogue/odoo-field-mapping-draft.md.

This module never talks to Odoo itself — it classifies a `fields_by_model` dict
already produced by discovery/fields.py (or `None`, meaning discovery never ran).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.integrations.odoo.models import OdooFieldDescriptor


class MappingClassification(StrEnum):
    STANDARD_FIELD_CONFIRMED = "STANDARD_FIELD_CONFIRMED"
    STANDARD_FIELD_PARTIAL = "STANDARD_FIELD_PARTIAL"
    CUSTOM_FIELD_EXISTS = "CUSTOM_FIELD_EXISTS"
    CUSTOM_FIELD_REQUIRED = "CUSTOM_FIELD_REQUIRED"
    POSTGRESQL_ONLY = "POSTGRESQL_ONLY"
    DERIVED = "DERIVED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    REQUIRES_BUSINESS_DECISION = "REQUIRES_BUSINESS_DECISION"
    REQUIRES_ODOO_CONFIGURATION = "REQUIRES_ODOO_CONFIGURATION"


class Evidence(StrEnum):
    VERIFIED_FACT = "VERIFIED_FACT"
    INFERRED_MAPPING = "INFERRED_MAPPING"
    UNVERIFIED_ASSUMPTION = "UNVERIFIED_ASSUMPTION"


@dataclass(frozen=True)
class FieldMapping:
    canonical_field: str
    odoo_model: str | None
    odoo_field: str | None
    classification: MappingClassification
    evidence: Evidence
    notes: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "canonical_field": self.canonical_field,
            "odoo_model": self.odoo_model,
            "odoo_field": self.odoo_field,
            "classification": self.classification.value,
            "evidence": self.evidence.value,
            "notes": self.notes,
        }


FieldsByModel = Mapping[str, Mapping[str, OdooFieldDescriptor] | None]


def _classify(
    fields_by_model: FieldsByModel | None,
    canonical_field: str,
    odoo_model: str | None,
    odoo_field: str | None,
    *,
    if_present: MappingClassification,
    if_absent: MappingClassification,
    if_no_evidence: MappingClassification,
    notes: str,
) -> FieldMapping:
    if odoo_model is None or odoo_field is None:
        return FieldMapping(
            canonical_field,
            odoo_model,
            odoo_field,
            if_no_evidence,
            Evidence.UNVERIFIED_ASSUMPTION,
            notes,
        )

    if fields_by_model is None:
        return FieldMapping(
            canonical_field,
            odoo_model,
            odoo_field,
            if_no_evidence,
            Evidence.UNVERIFIED_ASSUMPTION,
            notes
            + " (no live Odoo discovery ran — draft mapping only, see odoo-field-mapping-draft.md)",
        )

    model_fields = fields_by_model.get(odoo_model)
    if model_fields is None:
        return FieldMapping(
            canonical_field,
            odoo_model,
            odoo_field,
            MappingClassification.NOT_SUPPORTED,
            Evidence.VERIFIED_FACT,
            notes + f" ({odoo_model} is not installed/accessible on this instance)",
        )

    if odoo_field in model_fields:
        return FieldMapping(
            canonical_field, odoo_model, odoo_field, if_present, Evidence.VERIFIED_FACT, notes
        )
    return FieldMapping(
        canonical_field,
        odoo_model,
        odoo_field,
        if_absent,
        Evidence.VERIFIED_FACT,
        notes + f" ({odoo_field!r} not found on {odoo_model} in fields_get)",
    )


def _postgresql_only(canonical_field: str, notes: str) -> FieldMapping:
    return FieldMapping(
        canonical_field,
        None,
        None,
        MappingClassification.POSTGRESQL_ONLY,
        Evidence.VERIFIED_FACT,
        notes,
    )


def build_category_mapping(fields_by_model: FieldsByModel | None) -> list[FieldMapping]:
    return [
        FieldMapping(
            "external_key",
            "ir.model.data",
            "name",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Standard Odoo external-id pattern — see "
            "docs/integrations/odoo-external-key-strategy.md; no xml_id is created in this phase.",
        ),
        _classify(
            fields_by_model,
            "code",
            "product.category",
            None,
            if_present=MappingClassification.NOT_SUPPORTED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.NOT_SUPPORTED,
            notes="No standard Odoo field for a short category code (D03) — stays PostgreSQL-only "
            "unless a genuine integration need for it inside Odoo is identified.",
        ),
        _classify(
            fields_by_model,
            "slug",
            "product.category",
            None,
            if_present=MappingClassification.NOT_SUPPORTED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.NOT_SUPPORTED,
            notes="No standard Odoo field for a URL slug — PostgreSQL-only, matches D06.",
        ),
        _classify(
            fields_by_model,
            "name_en",
            "product.category",
            "name",
            if_present=MappingClassification.STANDARD_FIELD_CONFIRMED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.STANDARD_FIELD_PARTIAL,
            notes="product.category.name is Odoo's standard category name field.",
        ),
        FieldMapping(
            "name_ar",
            "product.category",
            "name",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Requires Arabic (ar_001/ar_SA) installed and activated as an Odoo language, then a "
            "translated `name` value via ir.translation — not a separate field. Not checked by "
            "fields_get; verified via the language-activation check instead (see D13).",
        ),
        _postgresql_only(
            "description_en",
            "No standard product.category description field is used by this app's UI; "
            "treated as PostgreSQL/merchandising-owned like the rest of category copy.",
        ),
        _postgresql_only("description_ar", "Same as description_en."),
        _classify(
            fields_by_model,
            "parent category",
            "product.category",
            "parent_id",
            if_present=MappingClassification.STANDARD_FIELD_CONFIRMED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.STANDARD_FIELD_PARTIAL,
            notes="Not used today (D02: flat, 6 categories) — field exists in Odoo for future "
            "hierarchy.",
        ),
        _classify(
            fields_by_model,
            "active",
            "product.category",
            "active",
            if_present=MappingClassification.STANDARD_FIELD_CONFIRMED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.STANDARD_FIELD_PARTIAL,
            notes="Standard Odoo active flag.",
        ),
        _postgresql_only(
            "display order",
            "Storefront display order is Admin-owned merchandising data, not an Odoo concept "
            "(final-data-ownership.md).",
        ),
    ]


def build_product_mapping(fields_by_model: FieldsByModel | None) -> list[FieldMapping]:
    def std(canonical: str, odoo_field: str, notes: str) -> FieldMapping:
        return _classify(
            fields_by_model,
            canonical,
            "product.template",
            odoo_field,
            if_present=MappingClassification.STANDARD_FIELD_CONFIRMED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.STANDARD_FIELD_PARTIAL,
            notes=notes,
        )

    return [
        FieldMapping(
            "external_key",
            "ir.model.data",
            "name",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Same external-id strategy as categories — see identifier-mapping-register.md (D20).",
        ),
        _classify(
            fields_by_model,
            "sku",
            "product.product",
            "default_code",
            if_present=MappingClassification.STANDARD_FIELD_CONFIRMED,
            if_absent=MappingClassification.NOT_SUPPORTED,
            if_no_evidence=MappingClassification.STANDARD_FIELD_PARTIAL,
            notes="default_code ('Internal Reference') lives on the variant (product.product), not "
            "the template — 1:1 for single-variant products, per-variant for buttercream-cake.",
        ),
        _postgresql_only(
            "slug", "No standard Odoo field for a URL slug — PostgreSQL-only, matches D06."
        ),
        std("name_en", "name", "product.template.name is the standard product name field."),
        FieldMapping(
            "name_ar",
            "product.template",
            "name",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Same Arabic-translation caveat as category name_ar.",
        ),
        std(
            "description_en",
            "description_sale",
            "description_sale ('Sales Description') is the customer-facing field — description "
            "(internal notes) is the wrong target.",
        ),
        FieldMapping(
            "description_ar",
            "product.template",
            "description_sale",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Same Arabic-translation caveat.",
        ),
        _postgresql_only(
            "short description",
            "No standard Odoo field distinct from description_sale for a short/teaser "
            "description — PostgreSQL/merchandising-owned.",
        ),
        std("category", "categ_id", "Standard many2one to product.category."),
        std(
            "product type",
            "type",
            "Standard Odoo Consumable/Storable/Service classification (D10).",
        ),
        std("unit of measure", "uom_id", "Standard UoM field (D09)."),
        std("active", "active", "Standard Odoo active flag."),
        std("sellable", "sale_ok", "Standard 'Can be Sold' flag."),
        std(
            "base sales price",
            "list_price",
            "Standard template sales price — pricelist interaction is D08.",
        ),
        FieldMapping(
            "currency",
            "res.company",
            "currency_id",
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Company/pricelist currency setting, not a per-product field — verified via "
            "company_currency check (D07).",
        ),
        std(
            "tax mapping", "taxes_id", "Standard many2many to account.tax — real record TBD (D08)."
        ),
        std(
            "primary image", "image_1920", "Base64 image_1920; Odoo auto-derives smaller variants."
        ),
        FieldMapping(
            "additional images",
            "product.image",
            None,
            MappingClassification.REQUIRES_ODOO_CONFIGURATION,
            Evidence.INFERRED_MAPPING,
            "Extra Product Media gallery model (Odoo 15+) — see product.image "
            "model-availability check; only buttercream-cake needs this (3 gallery thumbnails).",
        ),
        FieldMapping(
            "product template ID",
            "product.template",
            "id",
            MappingClassification.DERIVED,
            Evidence.INFERRED_MAPPING,
            "Odoo's internal numeric id — stored alongside external_key, never used as the "
            "sync join key itself (numeric ids are not stable across a reimport).",
        ),
        FieldMapping(
            "product variant ID",
            "product.product",
            "id",
            MappingClassification.DERIVED,
            Evidence.INFERRED_MAPPING,
            "Same caveat as product template ID.",
        ),
    ]
