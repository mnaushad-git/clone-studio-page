from __future__ import annotations

from pydantic import BaseModel, Field


class DeliverySettingsOut(BaseModel):
    delivery_enabled: bool
    flat_delivery_fee: str
    free_delivery_threshold: str
    minimum_order_amount: str
    same_day_delivery_enabled: bool
    same_day_cutoff_time: str | None
    available_days: list[int]


class DeliverySettingsUpdateRequest(BaseModel):
    delivery_enabled: bool | None = None
    flat_delivery_fee: float | None = Field(default=None, ge=0)
    free_delivery_threshold: float | None = Field(default=None, ge=0)
    minimum_order_amount: float | None = Field(default=None, ge=0)
    same_day_delivery_enabled: bool | None = None
    same_day_cutoff_time: str | None = Field(default=None, max_length=5)
    available_days: list[int] | None = None


class DeliverySlotOut(BaseModel):
    id: str
    label: str
    start_time: str
    end_time: str
    max_orders_per_slot: int | None
    active: bool
    display_order: int


class DeliverySlotCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    start_time: str = Field(min_length=1, max_length=5)
    end_time: str = Field(min_length=1, max_length=5)
    max_orders_per_slot: int | None = Field(default=None, ge=1)
    active: bool = True
    display_order: int = Field(default=0, ge=0)


class DeliverySlotUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=64)
    start_time: str | None = Field(default=None, min_length=1, max_length=5)
    end_time: str | None = Field(default=None, min_length=1, max_length=5)
    max_orders_per_slot: int | None = Field(default=None, ge=1)
    active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class DeliveryOptionsOut(BaseModel):
    """Public shape served at GET /api/v1/checkout/delivery-options — the Storefront
    reads current delivery pricing/slots from here instead of admin-store's local
    zones/slots (task brief §12)."""

    delivery_enabled: bool
    flat_delivery_fee: str
    free_delivery_threshold: str
    minimum_order_amount: str
    same_day_delivery_enabled: bool
    same_day_cutoff_time: str | None
    available_days: list[int]
    slots: list[DeliverySlotOut]
