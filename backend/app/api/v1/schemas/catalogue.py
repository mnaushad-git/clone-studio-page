"""Pydantic response models for the read-only catalogue API (/api/v1/catalogue/...).

Every response crossing the route boundary is one of these — no hand-built dicts
(api-standards.md §3). Money is always a fixed-precision decimal string, never a raw
float, to avoid floating-point rounding artifacts on the wire.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    code: str
    slug: str
    name_en: str
    name_ar: str | None
    description_en: str | None
    description_ar: str | None
    display_order: int


class MomentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    slug: str
    name_en: str
    name_ar: str | None
    description_en: str | None
    description_ar: str | None
    display_order: int


class RecipientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    slug: str
    name_en: str
    name_ar: str | None
    description_en: str | None
    description_ar: str | None
    display_order: int


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    role: str
    alt_text_en: str | None
    alt_text_ar: str | None
    display_order: int


class VariantAttributeOut(BaseModel):
    """One axis of a variant's combination — the wire shape for
    `catalogue_product_attribute_values`, the single source of truth for per-axis
    data (see app/models/catalogue/product_attribute_value.py)."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name_en: str
    value_label_en: str


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    sku: str
    name_en: str
    is_default: bool
    attributes: list[VariantAttributeOut]
    price: str | None
    currency: str | None


class MerchandisingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    featured: bool
    is_new: bool
    is_bestseller: bool | None
    badge_en: str | None
    badge_ar: str | None


class ProductSummaryOut(BaseModel):
    """Shape used by the product-list and homepage endpoints — one row per product,
    default-variant price only (no gallery/variants/moments/recipients; fetch the
    detail endpoint for those)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    sku: str
    slug: str
    name_en: str
    name_ar: str | None
    short_description_en: str | None
    category: CategoryOut
    price: str
    currency: str
    price_includes_tax: bool | None
    primary_image: ImageOut | None
    merchandising: MerchandisingOut
    moments: list[MomentOut]
    recipients: list[RecipientOut]
    availability_status: str


class ProductDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_key: str
    sku: str
    slug: str
    name_en: str
    name_ar: str | None
    description_en: str | None
    description_ar: str | None
    category: CategoryOut
    price: str
    currency: str
    price_includes_tax: bool | None
    primary_image: ImageOut | None
    gallery_images: list[ImageOut]
    variants: list[VariantOut]
    merchandising: MerchandisingOut
    moments: list[MomentOut]
    recipients: list[RecipientOut]
    availability_status: str


class PaginatedProductsOut(BaseModel):
    items: list[ProductSummaryOut]
    total: int
    limit: int
    offset: int


class HomepageOut(BaseModel):
    hero: list[ProductSummaryOut]
    gifts: list[ProductSummaryOut]
    divine: list[ProductSummaryOut]
    chocolates: list[ProductSummaryOut]
    extras: list[ProductSummaryOut]
    new: list[ProductSummaryOut]
