"""Admin system-status endpoint (task brief §9). Any authenticated admin can view
it — knowing whether stub providers are active is safety-relevant for every role,
not a privileged operation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import get_current_admin, require_csrf, require_role
from app.api.v1.schemas.admin_system import (
    CacheInvalidateRequest,
    CacheInvalidateResponse,
    SystemStatusOut,
)
from app.cache import RedisCache, get_cache_client
from app.cache.invalidation import CacheInvalidationService
from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.dependencies import get_app_settings, get_db
from app.models.admin.admin_user import AdminUser
from app.services.admin.audit_service import AuditService
from app.services.admin.system_status_service import get_system_status

router = APIRouter(prefix="/system", tags=["admin-system"])

# Cache invalidation is an operational/ops action, not a merchandising edit — scoped
# to SUPER_ADMIN only (task brief §19: "SUPER_ADMIN or appropriate role only").
_CACHE_INVALIDATE_ROLES = ("SUPER_ADMIN",)


@router.get("/status", dependencies=[Depends(get_current_admin)])
def system_status() -> SystemStatusOut:
    status = get_system_status()
    stub_active = "stub" in (
        status.payment_provider_mode,
        status.notification_provider_mode,
        status.odoo_order_push_mode,
    )
    return SystemStatusOut(
        database=status.database,
        redis=status.redis,
        celery_worker=status.celery_worker,
        celery_beat=status.celery_beat,
        odoo=status.odoo,
        payment_provider_mode=status.payment_provider_mode,
        notification_provider_mode=status.notification_provider_mode,
        odoo_order_push_mode=status.odoo_order_push_mode,
        stub_providers_active=stub_active,
        cache_enabled=status.cache_enabled,
        cache_key_version=status.cache_key_version,
        cache_hits=status.cache_hits,
        cache_misses=status.cache_misses,
        cache_errors=status.cache_errors,
    )


@router.post("/cache/invalidate", dependencies=[Depends(require_csrf)])
def invalidate_cache(
    body: CacheInvalidateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_CACHE_INVALIDATE_ROLES)),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> CacheInvalidateResponse:
    if body.operation == "product" and not body.slug:
        raise ValidationAppError("`slug` is required when operation is 'product'.")

    invalidation = CacheInvalidationService(cache, settings)
    operations = {
        "homepage": invalidation.invalidate_homepage,
        "categories": invalidation.invalidate_categories,
        "moments": invalidation.invalidate_moments,
        "recipients": invalidation.invalidate_recipients,
        "product_lists": invalidation.invalidate_product_lists,
        "all": invalidation.invalidate_catalogue_all,
    }
    if body.operation == "product":
        assert body.slug is not None
        deleted = invalidation.invalidate_product(body.slug)
    else:
        deleted = operations[body.operation]()

    AuditService(session).record(
        admin=admin,
        admin_email=admin.email,
        action="admin.cache_invalidated",
        entity_type="cache",
        entity_id=body.slug,
        after={"operation": body.operation, "deleted_keys": deleted},
        request=request,
    )
    session.commit()

    return CacheInvalidateResponse(operation=body.operation, slug=body.slug, deleted_keys=deleted)
