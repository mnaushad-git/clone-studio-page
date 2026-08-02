"""Pydantic models for /api/v1/admin/catalogue-sync/* — run history and the manual
"Sync now" trigger for the Odoo -> PostgreSQL product pull sync."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminSyncItemOut(BaseModel):
    id: str
    entity_type: str
    odoo_model: str
    odoo_record_id: int
    postgres_entity_id: str | None
    match_strategy: str | None
    action: str
    result_status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime


class AdminSyncRunOut(BaseModel):
    id: str
    trigger: str
    status: str
    full_resync: bool
    started_at: datetime
    completed_at: datetime | None
    initiated_by: str
    total_created: int
    total_updated: int
    total_skipped: int
    total_failed: int
    counts_by_entity: dict[str, dict[str, int]] | None
    error_summary: str | None


class AdminSyncRunListOut(BaseModel):
    items: list[AdminSyncRunOut]
    total: int
    limit: int
    offset: int


class AdminSyncRunDetailOut(AdminSyncRunOut):
    items_detail: list[AdminSyncItemOut]


class AdminSyncTriggerRequest(BaseModel):
    full_resync: bool = Field(default=False)


class AdminSyncTriggerResponseOut(BaseModel):
    queued: bool
    worker_dispatched: bool
    message: str
