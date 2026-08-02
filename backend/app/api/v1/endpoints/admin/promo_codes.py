"""Admin promo-code endpoints (task brief §11). CATALOGUE_ADMIN + SUPER_ADMIN only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import require_csrf, require_role
from app.api.v1.schemas.admin_promo_codes import (
    PromoCodeCreateRequest,
    PromoCodeListOut,
    PromoCodeOut,
    PromoCodeUpdateRequest,
)
from app.dependencies import get_db
from app.models.admin.admin_user import AdminUser
from app.models.admin.promo_code import PromoCode
from app.services.admin.promo_admin_service import PromoAdminService

router = APIRouter(prefix="/promo-codes", tags=["admin-promo-codes"])

_ROLES = ("SUPER_ADMIN", "CATALOGUE_ADMIN")


def _money(amount: object | None) -> str | None:
    return None if amount is None else f"{float(amount):.2f}"  # type: ignore[arg-type]


def _promo_out(promo: PromoCode) -> PromoCodeOut:
    return PromoCodeOut(
        id=str(promo.id),
        code=promo.code,
        description=promo.description,
        discount_type=promo.discount_type,
        discount_value=_money(promo.discount_value) or "0.00",
        minimum_order_amount=_money(promo.minimum_order_amount) or "0.00",
        maximum_discount_amount=_money(promo.maximum_discount_amount),
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        usage_limit=promo.usage_limit,
        usage_count=promo.usage_count,
        per_customer_limit=promo.per_customer_limit,
        is_active=promo.is_active,
        created_at=promo.created_at,
        updated_at=promo.updated_at,
    )


@router.get("", dependencies=[Depends(require_role(*_ROLES))])
def list_promo_codes(
    session: Session = Depends(get_db),
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PromoCodeListOut:
    items, total = PromoAdminService(session).list_promo_codes(
        is_active=is_active, search=search, limit=limit, offset=offset
    )
    return PromoCodeListOut(
        items=[_promo_out(p) for p in items], total=total, limit=limit, offset=offset
    )


@router.post("", dependencies=[Depends(require_csrf)])
def create_promo_code(
    body: PromoCodeCreateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> PromoCodeOut:
    promo = PromoAdminService(session).create_promo_code(
        body.model_dump(), admin=admin, request=request
    )
    session.commit()
    return _promo_out(promo)


@router.get("/{promo_id}", dependencies=[Depends(require_role(*_ROLES))])
def get_promo_code(promo_id: uuid.UUID, session: Session = Depends(get_db)) -> PromoCodeOut:
    return _promo_out(PromoAdminService(session).get_promo_code(promo_id))


@router.patch("/{promo_id}", dependencies=[Depends(require_csrf)])
def update_promo_code(
    promo_id: uuid.UUID,
    body: PromoCodeUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> PromoCodeOut:
    updates = body.model_dump(exclude_unset=True)
    promo = PromoAdminService(session).update_promo_code(
        promo_id, updates, admin=admin, request=request
    )
    session.commit()
    return _promo_out(promo)


@router.delete("/{promo_id}", dependencies=[Depends(require_csrf)], status_code=204)
def delete_promo_code(
    promo_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> None:
    PromoAdminService(session).delete_promo_code(promo_id, admin=admin, request=request)
    session.commit()
