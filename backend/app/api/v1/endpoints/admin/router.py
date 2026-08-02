"""Assembles /api/v1/admin/*. Every sub-router except `auth` requires an
authenticated admin session at the router level (get_current_admin) — `auth` handles
its own per-endpoint auth since login/refresh must stay unauthenticated while
logout/me/change-password require a session.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps.admin_auth import get_current_admin
from app.api.v1.endpoints.admin import (
    audit,
    auth,
    catalogue_sync,
    dashboard,
    delivery,
    orders,
    products,
    promo_codes,
    system,
)

admin_router = APIRouter(prefix="/admin")

admin_router.include_router(auth.router)

_protected = APIRouter(dependencies=[Depends(get_current_admin)])
_protected.include_router(dashboard.router)
_protected.include_router(orders.router)
_protected.include_router(orders.payments_router)
_protected.include_router(products.router)
_protected.include_router(catalogue_sync.router)
_protected.include_router(promo_codes.router)
_protected.include_router(delivery.router)
_protected.include_router(delivery.slots_router)
_protected.include_router(audit.router)
_protected.include_router(system.router)

admin_router.include_router(_protected)
