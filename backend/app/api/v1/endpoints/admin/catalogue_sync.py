"""Admin endpoints for the Odoo -> PostgreSQL catalogue pull sync: run history plus a
manual "Sync now" trigger. Same role gate as admin product endpoints — no other role
has a catalogue-sync use case."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import require_csrf, require_role
from app.api.v1.schemas.admin_catalogue_sync import (
    AdminSyncItemOut,
    AdminSyncRunDetailOut,
    AdminSyncRunListOut,
    AdminSyncRunOut,
    AdminSyncTriggerRequest,
    AdminSyncTriggerResponseOut,
)
from app.dependencies import get_db
from app.models.admin.admin_user import AdminUser
from app.models.integration.odoo_catalogue_sync_item import OdooCatalogueSyncItem
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.services.admin.catalogue_sync_admin_service import CatalogueSyncAdminService

router = APIRouter(prefix="/catalogue-sync", tags=["admin-catalogue-sync"])

_ROLES = ("SUPER_ADMIN", "CATALOGUE_ADMIN")


def _run_out(run: OdooCatalogueSyncRun) -> AdminSyncRunOut:
    return AdminSyncRunOut(
        id=str(run.id),
        trigger=run.trigger,
        status=run.status,
        full_resync=run.full_resync,
        started_at=run.started_at,
        completed_at=run.completed_at,
        initiated_by=run.initiated_by,
        total_created=run.total_created,
        total_updated=run.total_updated,
        total_skipped=run.total_skipped,
        total_failed=run.total_failed,
        counts_by_entity=run.counts_by_entity_json,
        error_summary=run.error_summary,
    )


def _item_out(item: OdooCatalogueSyncItem) -> AdminSyncItemOut:
    return AdminSyncItemOut(
        id=str(item.id),
        entity_type=item.entity_type,
        odoo_model=item.odoo_model,
        odoo_record_id=item.odoo_record_id,
        postgres_entity_id=str(item.postgres_entity_id) if item.postgres_entity_id else None,
        match_strategy=item.match_strategy,
        action=item.action,
        result_status=item.result_status,
        error_code=item.error_code,
        error_message=item.error_message,
        created_at=item.created_at,
    )


@router.get("/runs", dependencies=[Depends(require_role(*_ROLES))])
def list_sync_runs(
    session: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> AdminSyncRunListOut:
    service = CatalogueSyncAdminService(session)
    runs = service.list_runs(limit=limit)
    return AdminSyncRunListOut(
        items=[_run_out(r) for r in runs], total=len(runs), limit=limit, offset=0
    )


@router.get("/runs/{run_id}", dependencies=[Depends(require_role(*_ROLES))])
def get_sync_run(run_id: uuid.UUID, session: Session = Depends(get_db)) -> AdminSyncRunDetailOut:
    service = CatalogueSyncAdminService(session)
    run = service.get_run(run_id)
    items = service.get_run_items(run_id)
    return AdminSyncRunDetailOut(
        **_run_out(run).model_dump(), items_detail=[_item_out(i) for i in items]
    )


@router.post("/trigger", dependencies=[Depends(require_csrf)])
def trigger_sync(
    body: AdminSyncTriggerRequest,
    request: Request,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(require_role(*_ROLES)),
) -> AdminSyncTriggerResponseOut:
    result = CatalogueSyncAdminService(session).trigger_sync(
        full_resync=body.full_resync, admin=admin, request=request
    )
    session.commit()
    return AdminSyncTriggerResponseOut(
        queued=result.queued, worker_dispatched=result.worker_dispatched, message=result.message
    )
