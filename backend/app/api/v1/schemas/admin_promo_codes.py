from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PromoCodeOut(BaseModel):
    id: str
    code: str
    description: str | None
    discount_type: str
    discount_value: str
    minimum_order_amount: str
    maximum_discount_amount: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    usage_limit: int | None
    usage_count: int
    per_customer_limit: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PromoCodeListOut(BaseModel):
    items: list[PromoCodeOut]
    total: int
    limit: int
    offset: int


class PromoCodeCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    description: str | None = Field(default=None, max_length=2000)
    discount_type: str
    discount_value: float = Field(gt=0)
    minimum_order_amount: float = Field(default=0, ge=0)
    maximum_discount_amount: float | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    per_customer_limit: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @field_validator("discount_type")
    @classmethod
    def _valid_discount_type(cls, value: str) -> str:
        if value not in ("PERCENTAGE", "FIXED_AMOUNT"):
            raise ValueError("discount_type must be PERCENTAGE or FIXED_AMOUNT")
        return value


class PromoCodeUpdateRequest(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    discount_type: str | None = None
    discount_value: float | None = Field(default=None, gt=0)
    minimum_order_amount: float | None = Field(default=None, ge=0)
    maximum_discount_amount: float | None = Field(default=None, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    per_customer_limit: int | None = Field(default=None, ge=1)
    is_active: bool | None = None

    @field_validator("discount_type")
    @classmethod
    def _valid_discount_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ("PERCENTAGE", "FIXED_AMOUNT"):
            raise ValueError("discount_type must be PERCENTAGE or FIXED_AMOUNT")
        return value
