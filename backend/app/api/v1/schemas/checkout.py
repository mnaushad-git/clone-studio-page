"""Pydantic models for the checkout/order API (/api/v1/orders/...).

Money is always a fixed-precision decimal string on the wire (api-standards.md §3,
matches app/api/v1/schemas/catalogue.py). Every price/total in the response is computed
server-side from catalogue_product_prices — nothing here is ever taken from the request
as-is and echoed back.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutItemIn(BaseModel):
    product_slug: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1, le=99)
    # code -> selected value_label_en, e.g. {"size": "9 INCH", "flavor": "Chocolate"}
    # — one entry per axis the client saw on this product's VariantOut.attributes.
    # Any number of axes, not just the two legacy "size"/"flavor" slots.
    attributes: dict[str, str] = Field(default_factory=dict)
    inscription: str | None = Field(default=None, max_length=255)


class CheckoutCustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str = Field(min_length=1, max_length=32)


class CheckoutDeliveryIn(BaseModel):
    is_gift: bool = False
    identity_secret: bool = False
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=1, max_length=32)
    area: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    address_extra: str | None = Field(default=None, max_length=255)
    delivery_date: str | None = Field(default=None, max_length=64)
    delivery_time: str | None = Field(default=None, max_length=64)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItemIn] = Field(min_length=1, max_length=100)
    promo_code: str | None = Field(default=None, max_length=32)
    customer: CheckoutCustomerIn
    delivery: CheckoutDeliveryIn


class PayOrderRequest(BaseModel):
    method_label: str = Field(min_length=1, max_length=128)


class OrderItemAttributeOut(BaseModel):
    """Snapshot of one selected axis, taken at order-creation time — mirrors
    app/api/v1/schemas/catalogue.py's VariantAttributeOut (duplicated, not shared, per
    this codebase's convention of small per-schema-file DTOs)."""

    code: str
    name_en: str
    value_label_en: str


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name_en: str
    attributes: list[OrderItemAttributeOut]
    inscription: str | None
    quantity: int
    unit_price: str
    line_total: str


class OrderStatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    occurred_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_number: str
    status: str
    currency: str
    subtotal_amount: str
    discount_amount: str
    promo_code: str | None
    tax_amount: str
    delivery_fee_amount: str
    total_amount: str
    is_gift: bool
    recipient_name: str
    recipient_phone: str
    delivery_area: str | None
    delivery_address: str | None
    delivery_address_extra: str | None
    delivery_date: str | None
    delivery_time: str | None
    tracking_token: str
    payment_method: str | None
    items: list[OrderItemOut]
    status_history: list[OrderStatusEventOut]
    created_at: datetime
