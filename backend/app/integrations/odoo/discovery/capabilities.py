"""Orchestrates the phase's environment-verification checklist (items 1-23) into one
structured, JSON-serializable report. Every check is independent — one failing check
(e.g. a missing model) never aborts the others, so the report always reflects the
full picture reachable from wherever verification actually got to.

Distinguishes, per check, exactly the four states the phase brief asks for:
  VERIFIED    — a live fact observed on this run, backed by a real Odoo response.
  BLOCKED     — attempted and failed (connectivity, auth, access, missing model/field).
  UNVERIFIED  — not attempted at all, because an earlier prerequisite (reachability,
                authentication) already failed.
  NOT_APPLICABLE — the check doesn't apply given an earlier verified fact (e.g. a
                gallery-model check when the base model itself isn't installed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooIntegrationError
from app.integrations.odoo.models import AvailabilityStatus, OdooServerVersion, OdooSession
from app.integrations.odoo.repositories.categories import OdooCategoryRepository
from app.integrations.odoo.repositories.metadata import MetadataRepository


class CheckStatus(StrEnum):
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class CapabilityCheck:
    check_id: str
    description: str
    status: CheckStatus
    detail: str | None = None
    evidence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "description": self.description,
            "status": self.status.value,
            "detail": self.detail,
            "evidence": self.evidence,
        }


@dataclass
class EnvironmentReport:
    generated_at: datetime
    protocol: str
    base_url: str
    database: str
    server_version: OdooServerVersion | None = None
    session: OdooSession | None = None
    checks: list[CapabilityCheck] = field(default_factory=list)

    @property
    def blockers(self) -> list[CapabilityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.BLOCKED]

    @property
    def overall_status(self) -> str:
        if self.session is None:
            return "BLOCKED"
        if self.blockers:
            return "PARTIAL"
        return "VERIFIED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "protocol": self.protocol,
            "base_url": self.base_url,
            "database": self.database,
            "overall_status": self.overall_status,
            "server_version": (
                {
                    "server_version": self.server_version.server_version,
                    "server_serie": self.server_version.server_serie,
                    "protocol_version": self.server_version.protocol_version,
                }
                if self.server_version
                else None
            ),
            "authenticated": self.session is not None,
            "authenticated_uid": self.session.uid if self.session else None,
            "checks": [c.to_dict() for c in self.checks],
            "blocking_check_ids": [c.check_id for c in self.blockers],
        }


# Verification items 6-14: model availability. (model_name, description, required)
# "required" models block overall readiness; non-required ones (gallery/company) are
# informational — their absence changes the import plan, not whether the phase is blocked.
REQUIRED_MODELS: list[tuple[str, str, bool]] = [
    ("product.template", "Product template model availability", True),
    ("product.product", "Product variant model availability", True),
    ("product.category", "Product category model availability", True),
    ("account.tax", "Tax model availability", True),
    ("uom.uom", "Unit-of-measure model availability", True),
    ("res.currency", "Currency model availability", True),
    ("product.pricelist", "Pricelist model availability", True),
    ("stock.quant", "Stock quantity/availability model availability", True),
    ("stock.warehouse", "Warehouse model availability", False),
    ("product.image", "Multiple image/gallery capability (Odoo 15+)", False),
    # Variant-attribute modelling (product.attribute -> product.attribute.value ->
    # product.template.attribute.line, auto-generating product.product per combination)
    # — non-required: the core category/template import already succeeds without it,
    # only real variant products (today: buttercream-cake) need these.
    ("product.attribute", "Product attribute model availability", False),
    ("product.attribute.value", "Product attribute value model availability", False),
    (
        "product.template.attribute.line",
        "Template-attribute-line model availability (drives variant auto-generation)",
        False,
    ),
    (
        "product.template.attribute.value",
        "Template-attribute-value model availability (carries price_extra)",
        False,
    ),
]

# Verification items 14-19: specific field presence. (model, field, description)
FIELD_CHECKS: list[tuple[str, str, str]] = [
    ("product.template", "image_1920", "Image field availability"),
    ("product.template", "barcode", "Product barcode field availability"),
    ("product.template", "description_sale", "Sales description field availability"),
    ("product.template", "default_code", "SKU/internal-reference field (template)"),
    ("product.product", "default_code", "SKU/internal-reference field (variant)"),
    ("product.template", "sale_ok", "Sellable field name"),
    ("product.template", "active", "Active field name"),
    ("product.template", "type", "Product type field availability"),
    (
        "product.template",
        "attribute_line_ids",
        "Whether variants are automatically created for templates (attribute lines)",
    ),
    (
        "product.attribute",
        "create_variant",
        "Attribute variant-creation mode field (must support 'always' for this app's model)",
    ),
    (
        "product.template.attribute.value",
        "price_extra",
        "Per-template attribute-value price surcharge field availability",
    ),
]


def run_environment_verification(
    config: OdooConfig, client: OdooClient, *, correlation_id: str | None = None
) -> EnvironmentReport:
    generated_at = datetime.now(UTC)
    checks: list[CapabilityCheck] = []

    server_version = _check_reachability(client, checks, correlation_id=correlation_id)
    if server_version is None:
        return EnvironmentReport(
            generated_at, config.protocol, config.base_url, config.database, None, None, checks
        )

    session = _check_authentication(client, checks, correlation_id=correlation_id)
    if session is None:
        _mark_remaining_unverified(checks)
        return EnvironmentReport(
            generated_at,
            config.protocol,
            config.base_url,
            config.database,
            server_version,
            None,
            checks,
        )

    metadata = MetadataRepository(client)
    _check_company_and_currency(metadata, config, checks, correlation_id=correlation_id)
    _check_required_models(metadata, checks, correlation_id=correlation_id)
    _check_fields(metadata, checks, correlation_id=correlation_id)
    _check_product_type_values(client, checks, correlation_id=correlation_id)
    _check_existing_category(client, checks, correlation_id=correlation_id)

    return EnvironmentReport(
        generated_at,
        config.protocol,
        config.base_url,
        config.database,
        server_version,
        session,
        checks,
    )


def _check_reachability(
    client: OdooClient, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> OdooServerVersion | None:
    try:
        version = client.get_server_version(correlation_id=correlation_id)
    except OdooIntegrationError as exc:
        checks.append(
            CapabilityCheck(
                "server_reachable", "Odoo server is reachable", CheckStatus.BLOCKED, str(exc)
            )
        )
        checks.append(
            CapabilityCheck(
                "server_version", "Odoo server version", CheckStatus.BLOCKED, "Server unreachable"
            )
        )
        return None

    checks.append(
        CapabilityCheck(
            "server_reachable",
            "Odoo server is reachable",
            CheckStatus.VERIFIED,
            evidence={"jsonrpc_endpoint": client.config.jsonrpc_endpoint},
        )
    )
    checks.append(
        CapabilityCheck(
            "server_version",
            "Odoo server version",
            CheckStatus.VERIFIED,
            evidence={
                "server_version": version.server_version,
                "server_serie": version.server_serie,
            },
        )
    )
    return version


def _check_authentication(
    client: OdooClient, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> OdooSession | None:
    try:
        session = client.authenticate(correlation_id=correlation_id)
    except OdooIntegrationError as exc:
        checks.append(
            CapabilityCheck(
                "authentication", "Authentication succeeds", CheckStatus.BLOCKED, str(exc)
            )
        )
        return None

    checks.append(
        CapabilityCheck(
            "authentication",
            "Authentication succeeds",
            CheckStatus.VERIFIED,
            evidence={"uid": session.uid, "database": session.database},
        )
    )
    return session


def _mark_remaining_unverified(checks: list[CapabilityCheck]) -> None:
    unverified_ids = (
        ["company_currency", "multi_company"]
        + [f"model_{name}" for name, _, _ in REQUIRED_MODELS]
        + [f"field_{model}_{field_name}" for model, field_name, _ in FIELD_CHECKS]
        + ["product_type_values", "existing_terrific_bites_category"]
    )
    descriptions = {
        "company_currency": "Selected company and company currency",
        "multi_company": "Whether multi-company/multi-currency behaviour applies",
        "product_type_values": "Product type field values supported by this version",
        "existing_terrific_bites_category": "Whether a Terrific Bites category already exists",
    }
    for name, description, _ in REQUIRED_MODELS:
        descriptions[f"model_{name}"] = description
    for model, field_name, description in FIELD_CHECKS:
        descriptions[f"field_{model}_{field_name}"] = description

    for check_id in unverified_ids:
        checks.append(
            CapabilityCheck(
                check_id,
                descriptions.get(check_id, check_id),
                CheckStatus.UNVERIFIED,
                "Skipped: authentication did not succeed",
            )
        )


def _check_company_and_currency(
    metadata: MetadataRepository,
    config: OdooConfig,
    checks: list[CapabilityCheck],
    *,
    correlation_id: str | None,
) -> None:
    try:
        companies = metadata.get_companies(correlation_id=correlation_id)
    except OdooIntegrationError as exc:
        checks.append(
            CapabilityCheck(
                "company_currency",
                "Selected company and company currency",
                CheckStatus.BLOCKED,
                str(exc),
            )
        )
        checks.append(
            CapabilityCheck(
                "multi_company",
                "Whether multi-company/multi-currency behaviour applies",
                CheckStatus.BLOCKED,
                str(exc),
            )
        )
        return

    selected = None
    if config.company_id:
        selected = next((c for c in companies if c.id == config.company_id), None)
    elif companies:
        selected = companies[0]

    if selected:
        checks.append(
            CapabilityCheck(
                "company_currency",
                "Selected company and company currency",
                CheckStatus.VERIFIED,
                evidence={
                    "company_id": selected.id,
                    "company_name": selected.name,
                    "currency_id": selected.currency_id,
                    "currency_name": selected.currency_name,
                },
            )
        )
    else:
        checks.append(
            CapabilityCheck(
                "company_currency",
                "Selected company and company currency",
                CheckStatus.BLOCKED,
                "No company found, or ODOO_COMPANY_ID did not match any existing company",
            )
        )

    checks.append(
        CapabilityCheck(
            "multi_company",
            "Whether multi-company/multi-currency behaviour applies",
            CheckStatus.VERIFIED,
            evidence={
                "company_count": len(companies),
                "distinct_currencies": sorted(
                    {c.currency_name for c in companies if c.currency_name}
                ),
            },
        )
    )


def _check_required_models(
    metadata: MetadataRepository, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> None:
    for model_name, description, required in REQUIRED_MODELS:
        try:
            availability = metadata.model_availability(model_name, correlation_id=correlation_id)
        except OdooIntegrationError as exc:
            checks.append(
                CapabilityCheck(f"model_{model_name}", description, CheckStatus.BLOCKED, str(exc))
            )
            continue

        if availability.status == AvailabilityStatus.AVAILABLE:
            status = CheckStatus.VERIFIED
        elif required:
            status = CheckStatus.BLOCKED
        else:
            status = CheckStatus.NOT_APPLICABLE
        checks.append(
            CapabilityCheck(
                f"model_{model_name}",
                description,
                status,
                availability.detail,
                evidence={"status": availability.status.value},
            )
        )


def _check_fields(
    metadata: MetadataRepository, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> None:
    for model_name, field_name, description in FIELD_CHECKS:
        check_id = f"field_{model_name}_{field_name}"
        try:
            exists = metadata.field_exists(model_name, field_name, correlation_id=correlation_id)
        except OdooIntegrationError as exc:
            checks.append(CapabilityCheck(check_id, description, CheckStatus.BLOCKED, str(exc)))
            continue
        checks.append(
            CapabilityCheck(
                check_id,
                description,
                CheckStatus.VERIFIED if exists else CheckStatus.BLOCKED,
                None if exists else f"Field {field_name!r} not found on {model_name}",
                evidence={"exists": exists},
            )
        )


def _check_product_type_values(
    client: OdooClient, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> None:
    try:
        fields = client.fields_get("product.template", ["type"], correlation_id=correlation_id)
    except OdooIntegrationError as exc:
        checks.append(
            CapabilityCheck(
                "product_type_values",
                "Product type field values supported by this version",
                CheckStatus.BLOCKED,
                str(exc),
            )
        )
        return

    type_field = fields.get("type")
    values = (
        [pair[0] for pair in type_field.selection] if type_field and type_field.selection else []
    )
    checks.append(
        CapabilityCheck(
            "product_type_values",
            "Product type field values supported by this version",
            CheckStatus.VERIFIED if values else CheckStatus.BLOCKED,
            None if values else "type field has no selection values",
            evidence={"values": values},
        )
    )


def _check_existing_category(
    client: OdooClient, checks: list[CapabilityCheck], *, correlation_id: str | None
) -> None:
    try:
        categories = OdooCategoryRepository(client)
        matches = categories.find_terrific_bites_categories(correlation_id=correlation_id)
    except OdooIntegrationError as exc:
        checks.append(
            CapabilityCheck(
                "existing_terrific_bites_category",
                "Whether a Terrific Bites category already exists",
                CheckStatus.BLOCKED,
                str(exc),
            )
        )
        return

    checks.append(
        CapabilityCheck(
            "existing_terrific_bites_category",
            "Whether a Terrific Bites category already exists",
            CheckStatus.VERIFIED,
            evidence={"match_count": len(matches), "matches": matches},
        )
    )
