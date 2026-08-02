"""Admin product endpoints (task brief §10). CATALOGUE_ADMIN + SUPER_ADMIN only —
view is read-only for everyone else in scope this MVP (no other role has a product
use case, per the plan's role matrix)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import require_csrf, require_role
from app.api.v1.schemas.admin_products import (
    AdminProductDetailOut,
    AdminProductListItemOut,
    AdminProductListOut,
    AdminProductMerchandisingOut,
    AdminProductMerchandisingUpdateRequest,
    AdminProductVariantOut,
)
from app.cache import RedisCache, get_cache_client
from app.cache.invalidation import CacheInvalidationService
from app.core.config import Settings
from app.core.exceptions import ValidationAppError
from app.dependencies import get_app_settings, get_db
from app.models.admin.admin_user import AdminUser
from app.models.catalogue.product import CatalogueProduct
from app.services.admin.product_admin_service import ProductAdminService
from app.services.catalogue.catalogue_query_service import _current_price, _image_out

router = APIRouter(prefix="/products", tags=["admin-products"])

_ROLES = ("SUPER_ADMIN", "CATALOGUE_ADMIN")


def _list_item_out(
    product: CatalogueProduct, service: ProductAdminService
) -> AdminProductListItemOut:
    price, currency = service.price_and_currency(product)
    merch = product.merchandising
    return AdminProductListItemOut(
        id=str(product.id),
        sku=product.sku,
        name_en=product.name_en,
        category_name=product.category.name_en,
        price=price,
        currency=currency,
        primary_image_url=service.primary_image_url(product),
        active=product.active,
        featured=merch.featured if merch else False,
        is_bestseller=merch.is_bestseller if merch else None,
        is_new=merch.is_new if merch else False,
        odoo_mapped=product.odoo_product_template_id is not None,
        last_synced_at=product.last_synced_at,
    )


def _detail_out(product: CatalogueProduct, service: ProductAdminService) -> AdminProductDetailOut:
    moment_names, recipient_names = service.moment_recipient_names(product)
    merch = product.merchandising
    variants = [
        AdminProductVariantOut(
            id=str(v.id),
            sku=v.sku,
            name_en=v.name_en,
            is_default=v.is_default,
            price=(lambda p: f"{float(p.amount):.2f}" if p else None)(_current_price(v)),
            currency=(lambda p: p.currency if p else None)(_current_price(v)),
        )
        for v in product.variants
    ]
    image_urls = [
        mapped.url
        for img in sorted(product.images, key=lambda i: i.display_order)
        if (mapped := _image_out(img)) is not None
    ]

    return AdminProductDetailOut(
        id=str(product.id),
        sku=product.sku,
        slug=product.slug,
        name_en=product.name_en,
        name_ar=product.name_ar,
        category_name=product.category.name_en,
        active=product.active,
        sellable=product.sellable,
        odoo_product_template_id=product.odoo_product_template_id,
        last_synced_at=product.last_synced_at,
        variants=variants,
        image_urls=image_urls,
        merchandising=AdminProductMerchandisingOut(
            storefront_visible=merch.storefront_visible if merch else True,
            featured=merch.featured if merch else False,
            is_new=merch.is_new if merch else False,
            is_bestseller=merch.is_bestseller if merch else None,
            display_order=merch.display_order if merch else 0,
            badge_en=merch.badge_en if merch else None,
            badge_ar=merch.badge_ar if merch else None,
        ),
        moment_names=moment_names,
        recipient_names=recipient_names,
    )


@router.get("", dependencies=[Depends(require_role(*_ROLES))])
def list_products(
    session: Session = Depends(get_db),
    category: str | None = Query(default=None, description="Category slug"),
    active: bool | None = None,
    featured: bool | None = None,
    bestseller: bool | None = None,
    new: bool | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminProductListOut:
    service = ProductAdminService(session)
    items, total = service.list_products(
        category_slug=category,
        active=active,
        featured=featured,
        is_bestseller=bestseller,
        is_new=new,
        search=search,
        limit=limit,
        offset=offset,
    )
    return AdminProductListOut(
        items=[_list_item_out(p, service) for p in items], total=total, limit=limit, offset=offset
    )


@router.get("/{product_id}", dependencies=[Depends(require_role(*_ROLES))])
def get_product(product_id: uuid.UUID, session: Session = Depends(get_db)) -> AdminProductDetailOut:
    service = ProductAdminService(session)
    product = service.get_product(product_id)
    return _detail_out(product, service)


@router.patch("/{product_id}/merchandising", dependencies=[Depends(require_csrf)])
def update_merchandising(
    product_id: uuid.UUID,
    body: AdminProductMerchandisingUpdateRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> AdminProductDetailOut:
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationAppError("No fields provided to update.")

    service = ProductAdminService(session)
    service.update_merchandising(product_id, updates, admin=admin, request=request)
    session.commit()

    product = service.get_product(product_id)

    # Invalidation happens strictly after the commit above — best-effort, never
    # raises (RedisCache swallows Redis failures), so a Redis outage can't turn a
    # successful merchandising edit into a failed request.
    CacheInvalidationService(cache, settings).invalidate_after_merchandising_update(product.slug)

    return _detail_out(product, service)
