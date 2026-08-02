"""Admin-facing surface for the Odoo -> PostgreSQL catalogue pull sync: run history
and a manual "Sync now" trigger. Mirrors OrderAdminService's best-effort Celery
dispatch pattern (task brief §9: never pretend a job was queued when the worker is
unavailable) — Celery Beat's periodic schedule is what actually guarantees the sync
runs even if this dispatch is lost to a broker hiccup.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.exceptions import NotFoundError
from app.models.admin.admin_user import AdminUser
from app.models.integration.odoo_catalogue_sync_item import OdooCatalogueSyncItem
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.repositories.integration.odoo_catalogue_sync_item_repository import (
    OdooCatalogueSyncItemRepository,
)
from app.repositories.integration.odoo_catalogue_sync_run_repository import (
    OdooCatalogueSyncRunRepository,
)
from app.services.admin.audit_service import AuditService


@dataclass(frozen=True)
class SyncTriggerResult:
    queued: bool
    worker_dispatched: bool
    message: str


class CatalogueSyncAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.sync_runs = OdooCatalogueSyncRunRepository(session)
        self.sync_items = OdooCatalogueSyncItemRepository(session)
        self.audit = AuditService(session)

    def list_runs(self, *, limit: int = 20) -> Sequence[OdooCatalogueSyncRun]:
        return self.sync_runs.list_recent(limit=limit)

    def get_run(self, run_id: uuid.UUID) -> OdooCatalogueSyncRun:
        run = self.sync_runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError(f"No catalogue sync run found with id {run_id}.")
        return run

    def get_run_items(self, run_id: uuid.UUID) -> Sequence[OdooCatalogueSyncItem]:
        return self.sync_items.list_for_run(run_id)

    def trigger_sync(
        self, *, full_resync: bool, admin: AdminUser, request: Request | None = None
    ) -> SyncTriggerResult:
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.catalogue_sync_triggered",
            entity_type="catalogue_sync",
            after={"full_resync": full_resync},
            request=request,
        )

        # Imported here (not at module scope) so importing this service never forces
        # Celery app construction — the same reasoning order_admin_service.py follows
        # for its .delay() imports.
        from app.workers.tasks.catalogue_sync import sync_catalogue_from_odoo

        try:
            sync_catalogue_from_odoo.delay(
                full_resync=full_resync, trigger="MANUAL", initiated_by=admin.email
            )
            return SyncTriggerResult(
                queued=True, worker_dispatched=True, message="Sync queued and dispatched."
            )
        except Exception:  # noqa: BLE001 - broker/Redis being down must not fail the request
            return SyncTriggerResult(
                queued=True,
                worker_dispatched=False,
                message=(
                    "Sync queued, but worker infrastructure is unavailable right now — it will "
                    "run on the next scheduled sync."
                ),
            )
