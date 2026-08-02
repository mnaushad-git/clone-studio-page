"""Admin promo-code CRUD (task brief §11). Discount validity rules (percentage 0-100,
fixed > 0, valid_until after valid_from, usage within limit) are enforced by both this
service and the promo_codes table's CHECK constraints — the service layer exists to
turn a would-be constraint-violation 500 into a proper 422/409 with a clear message.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.admin.admin_user import AdminUser
from app.models.admin.promo_code import PromoCode
from app.repositories.admin.promo_code_repository import PromoCodeRepository
from app.services.admin.audit_service import AuditService


class PromoAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = PromoCodeRepository(session)
        self.audit = AuditService(session)

    def list_promo_codes(
        self,
        *,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[PromoCode], int]:
        return self.repo.search(is_active=is_active, search=search, limit=limit, offset=offset)

    def get_promo_code(self, promo_id: uuid.UUID) -> PromoCode:
        promo = self.repo.get_by_id(promo_id)
        if promo is None:
            raise NotFoundError(f"No promo code found with id {promo_id}.")
        return promo

    @staticmethod
    def _validate_dates(valid_from: datetime | None, valid_until: datetime | None) -> None:
        if valid_from and valid_until and valid_until <= valid_from:
            raise ValidationAppError("valid_until must be after valid_from.")

    def create_promo_code(
        self, data: dict[str, Any], *, admin: AdminUser, request: Request | None = None
    ) -> PromoCode:
        code = str(data["code"]).strip().upper()
        if self.repo.get_by_code(code) is not None:
            raise ConflictError(f"Promo code {code!r} already exists.")
        self._validate_dates(data.get("valid_from"), data.get("valid_until"))

        promo = PromoCode(
            code=code,
            description=data.get("description"),
            discount_type=data["discount_type"],
            discount_value=data["discount_value"],
            minimum_order_amount=data.get("minimum_order_amount", 0),
            maximum_discount_amount=data.get("maximum_discount_amount"),
            valid_from=data.get("valid_from"),
            valid_until=data.get("valid_until"),
            usage_limit=data.get("usage_limit"),
            per_customer_limit=data.get("per_customer_limit"),
            is_active=data.get("is_active", True),
            created_by=admin.id,
            updated_by=admin.id,
        )
        try:
            self.repo.create(promo)
        except IntegrityError as exc:
            raise ValidationAppError(
                "Promo code violates a database constraint (check discount value/dates)."
            ) from exc

        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.promo_code_created",
            entity_type="promo_code",
            entity_id=str(promo.id),
            after={"code": promo.code, "discount_type": promo.discount_type},
            request=request,
        )
        return promo

    def update_promo_code(
        self,
        promo_id: uuid.UUID,
        data: dict[str, Any],
        *,
        admin: AdminUser,
        request: Request | None = None,
    ) -> PromoCode:
        promo = self.get_promo_code(promo_id)

        valid_from = data.get("valid_from", promo.valid_from)
        valid_until = data.get("valid_until", promo.valid_until)
        self._validate_dates(valid_from, valid_until)

        new_usage_limit = data.get("usage_limit", promo.usage_limit)
        if new_usage_limit is not None and promo.usage_count > new_usage_limit:
            raise ValidationAppError(
                f"usage_limit ({new_usage_limit}) cannot be lower than the current "
                f"usage_count ({promo.usage_count})."
            )

        before = {field: getattr(promo, field) for field in data}
        for field, value in data.items():
            setattr(promo, field, value)
        promo.updated_by = admin.id

        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValidationAppError(
                "Promo code update violates a database constraint (check discount value/dates)."
            ) from exc

        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.promo_code_updated",
            entity_type="promo_code",
            entity_id=str(promo.id),
            before=before,
            after=dict(data),
            request=request,
        )
        return promo

    def delete_promo_code(
        self, promo_id: uuid.UUID, *, admin: AdminUser, request: Request | None = None
    ) -> None:
        promo = self.get_promo_code(promo_id)
        if promo.usage_count > 0:
            raise ConflictError(
                f"Promo code {promo.code!r} has been used {promo.usage_count} time(s) — "
                "deactivate it instead of deleting."
            )
        code = promo.code
        self.repo.delete(promo)
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.promo_code_deleted",
            entity_type="promo_code",
            entity_id=str(promo_id),
            before={"code": code},
            request=request,
        )
