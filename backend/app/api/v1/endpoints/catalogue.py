"""Read-only catalogue endpoints — PostgreSQL is the serving source (CLAUDE.md rule 2).

Route handlers stay thin: each one resolves a session, delegates to
CachedCatalogueQueryService (a cache-aside decorator over CatalogueQueryService — see
app/cache/catalogue_cache.py), and returns its result. No Odoo call, no business logic
here. Redis is purely an acceleration layer (task brief §16): every handler below
still returns correct data from PostgreSQL if CACHE_ENABLED=false or Redis is down.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.v1.schemas.catalogue import (
    CategoryOut,
    HomepageOut,
    MomentOut,
    PaginatedProductsOut,
    ProductDetailOut,
    RecipientOut,
)
from app.cache import RedisCache, get_cache_client
from app.cache.catalogue_cache import CachedCatalogueQueryService
from app.cache.keys import CACHE_KEY_VERSION
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.dependencies import get_app_settings, get_db

router = APIRouter(prefix="/catalogue", tags=["catalogue"])

_CACHE_HEADER = "X-Cache"
_CACHE_VERSION_HEADER = "X-Cache-Key-Version"


def _set_cache_headers(response: Response, settings: Settings, status: str) -> None:
    """Dev/non-prod observability only (task brief §8) — never exposes Redis host
    details, and stays off entirely in production regardless of CACHE_DEBUG_HEADERS_ENABLED."""
    if settings.app_env == "production" or not settings.cache_debug_headers_enabled:
        return
    response.headers[_CACHE_HEADER] = status
    response.headers[_CACHE_VERSION_HEADER] = CACHE_KEY_VERSION


def _cached_service(
    session: Session, cache: RedisCache, settings: Settings
) -> CachedCatalogueQueryService:
    return CachedCatalogueQueryService(session, cache, settings)


@router.get("/categories", summary="List active catalogue categories")
def list_categories(
    response: Response,
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> list[CategoryOut]:
    value, status = _cached_service(session, cache, settings).list_categories()
    _set_cache_headers(response, settings, status)
    return value


@router.get("/moments", summary="List active catalogue moments")
def list_moments(
    response: Response,
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> list[MomentOut]:
    value, status = _cached_service(session, cache, settings).list_moments()
    _set_cache_headers(response, settings, status)
    return value


@router.get("/recipients", summary="List active catalogue recipients")
def list_recipients(
    response: Response,
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> list[RecipientOut]:
    value, status = _cached_service(session, cache, settings).list_recipients()
    _set_cache_headers(response, settings, status)
    return value


@router.get("/homepage", summary="Homepage catalogue sections")
def get_homepage(
    response: Response,
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> HomepageOut:
    value, status = _cached_service(session, cache, settings).get_homepage()
    _set_cache_headers(response, settings, status)
    return value


@router.get("/products", summary="List/filter/search/paginate active products")
def list_products(
    response: Response,
    category: str | None = Query(default=None, description="Category slug"),
    moment: str | None = Query(default=None, description="Moment slug"),
    recipient: str | None = Query(default=None, description="Recipient slug"),
    featured: bool | None = Query(default=None),
    bestseller: bool | None = Query(default=None),
    new: bool | None = Query(default=None, description="Filter by the is_new merchandising flag"),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> PaginatedProductsOut:
    value, status = _cached_service(session, cache, settings).list_products(
        category_slug=category,
        moment_slug=moment,
        recipient_slug=recipient,
        featured=featured,
        is_bestseller=bestseller,
        is_new=new,
        search=search,
        limit=limit,
        offset=offset,
    )
    _set_cache_headers(response, settings, status)
    return value


@router.get("/products/{slug}", summary="Product detail by slug")
def get_product_detail(
    slug: str,
    response: Response,
    session: Session = Depends(get_db),
    cache: RedisCache = Depends(get_cache_client),
    settings: Settings = Depends(get_app_settings),
) -> ProductDetailOut:
    detail, status = _cached_service(session, cache, settings).get_product_detail(slug)
    _set_cache_headers(response, settings, status)
    if detail is None:
        raise NotFoundError(f"No active product found with slug {slug!r}")
    return detail
