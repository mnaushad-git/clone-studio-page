"""Pydantic models for /api/v1/admin/auth/*. AdminUserOut never includes
password_hash — task brief §2: "Do not expose password hashes in API responses."
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class AdminChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class AdminUserOut(BaseModel):
    """Built explicitly in endpoint code (never via model_validate on the ORM
    object) — every UUID/Decimal field needs str-conversion first, same convention
    as app/api/v1/endpoints/orders.py's _order_out."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
