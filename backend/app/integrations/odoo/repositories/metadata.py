"""Server metadata, model availability, and access-rights discovery.

Backs verification items 1-6 and 20-23 of the phase checklist (server reachable,
version, auth, company/currency context, read access to required models, model
availability).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.exceptions import OdooIntegrationError
from app.integrations.odoo.models import AccessRights, AvailabilityStatus, ModelAvailability


@dataclass(frozen=True)
class CompanyInfo:
    id: int
    name: str
    currency_id: int | None
    currency_name: str | None


class MetadataRepository:
    def __init__(self, client: OdooClient) -> None:
        self._client = client

    def model_exists(self, model_name: str, *, correlation_id: str | None = None) -> bool:
        """True if `model_name` is a registered model on this instance (queried via
        `ir.model`, itself always readable by any authenticated user) — distinct from
        whether the current user can *read data from* the model, which is
        `model_availability` below.
        """
        count = self._client.search_count(
            "ir.model", [["model", "=", model_name]], correlation_id=correlation_id
        )
        return count > 0

    def model_availability(
        self, model_name: str, *, correlation_id: str | None = None
    ) -> ModelAvailability:
        if not self.model_exists(model_name, correlation_id=correlation_id):
            return ModelAvailability(
                model=model_name,
                status=AvailabilityStatus.UNAVAILABLE,
                detail="Model not installed",
            )
        try:
            access = self._client.check_access_rights(
                model_name, "read", correlation_id=correlation_id
            )
        except OdooIntegrationError as exc:
            return ModelAvailability(
                model=model_name, status=AvailabilityStatus.UNKNOWN, detail=str(exc)
            )
        if not access.allowed:
            return ModelAvailability(
                model=model_name,
                status=AvailabilityStatus.NO_ACCESS,
                detail="Model exists but the authenticated user lacks read access",
            )
        return ModelAvailability(model=model_name, status=AvailabilityStatus.AVAILABLE)

    def check_access(
        self, model_name: str, operation: str, *, correlation_id: str | None = None
    ) -> AccessRights:
        return self._client.check_access_rights(
            model_name, operation, correlation_id=correlation_id
        )

    def field_exists(
        self, model_name: str, field_name: str, *, correlation_id: str | None = None
    ) -> bool:
        # Restricting to [field_name] means Odoo only documents that one field (a
        # much smaller response than a full fields_get) — Odoo silently omits it
        # from the result if it doesn't exist, rather than erroring, so the `in`
        # check below is correct either way.
        fields = self._client.fields_get(model_name, [field_name], correlation_id=correlation_id)
        return field_name in fields

    def get_companies(self, *, correlation_id: str | None = None) -> list[CompanyInfo]:
        page = self._client.search_read(
            "res.company",
            [],
            ["id", "name", "currency_id"],
            correlation_id=correlation_id,
        )
        companies: list[CompanyInfo] = []
        for record in page.records:
            currency = record.get("currency_id")
            currency_id, currency_name = (currency[0], currency[1]) if currency else (None, None)
            companies.append(
                CompanyInfo(
                    id=record["id"],
                    name=record.get("name", ""),
                    currency_id=currency_id,
                    currency_name=currency_name,
                )
            )
        return companies
