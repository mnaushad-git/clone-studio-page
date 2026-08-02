"""Pydantic models for /api/v1/admin/products/*. Only merchandising (PostgreSQL-
owned) fields are writable — SKU/price/Odoo identity/tax/UoM/inventory stay
Odoo-owned and read-only here (task brief §10)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminProductListItemOut(BaseModel):
    id: str
    sku: str
    name_en: str
    category_name: str
    price: str | None
    currency: str | None
    primary_image_url: str | None
    active: bool
    featured: bool
    is_bestseller: bool | None
    is_new: bool
    odoo_mapped: bool
    last_synced_at: datetime | None


class AdminProductListOut(BaseModel):
    items: list[AdminProductListItemOut]
    total: int
    limit: int
    offset: int


class AdminProductVariantOut(BaseModel):
    id: str
    sku: str
    name_en: str
    is_default: bool
    price: str | None
    currency: str | None


class AdminProductMerchandisingOut(BaseModel):
    storefront_visible: bool
    featured: bool
    is_new: bool
    is_bestseller: bool | None
    display_order: int
    badge_en: str | None
    badge_ar: str | None


class AdminProductDetailOut(BaseModel):
    id: str
    sku: str
    slug: str
    name_en: str
    name_ar: str | None
    category_name: str
    active: bool
    sellable: bool
    odoo_product_template_id: int | None
    last_synced_at: datetime | None
    variants: list[AdminProductVariantOut]
    image_urls: list[str]
    merchandising: AdminProductMerchandisingOut
    moment_names: list[str]
    recipient_names: list[str]


class AdminProductMerchandisingUpdateRequest(BaseModel):
    """Every field optional — PATCH only updates what's provided."""

    featured: bool | None = None
    is_new: bool | None = None
    is_bestseller: bool | None = None
    storefront_visible: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    badge_en: str | None = Field(default=None, max_length=100)
    badge_ar: str | None = Field(default=None, max_length=100)
