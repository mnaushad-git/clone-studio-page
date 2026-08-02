from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SystemStatusOut(BaseModel):
    database: str
    redis: str
    celery_worker: str
    celery_beat: str
    odoo: str
    payment_provider_mode: str
    notification_provider_mode: str
    odoo_order_push_mode: str
    stub_providers_active: bool
    cache_enabled: bool
    cache_key_version: str
    cache_hits: int
    cache_misses: int
    cache_errors: int


CacheInvalidateOperation = Literal[
    "homepage", "categories", "product", "moments", "recipients", "product_lists", "all"
]


class CacheInvalidateRequest(BaseModel):
    operation: CacheInvalidateOperation
    # Required only when operation == "product" — never a raw Redis key (task brief
    # §19: "No arbitrary Redis command or raw key input").
    slug: str | None = None


class CacheInvalidateResponse(BaseModel):
    operation: CacheInvalidateOperation
    slug: str | None
    deleted_keys: int
