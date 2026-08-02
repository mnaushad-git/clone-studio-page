"""Celery task wrapping OdooCatalogueSyncService — the Odoo -> PostgreSQL product pull.
Dispatched both by Celery Beat (scheduled) and by the admin "Sync now" endpoint
(manual) with the exact same task, so the two triggers are provably identical in
behavior — they only differ in the `trigger`/`initiated_by` recorded on the run row.
"""

from __future__ import annotations

import logging
import uuid

from app.core.database import session_scope
from app.services.catalogue.odoo_catalogue_sync_service import OdooCatalogueSyncService
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.tasks.catalogue_sync")


@celery_app.task(
    name="app.workers.tasks.catalogue_sync.sync_catalogue_from_odoo",
    ignore_result=True,
)
def sync_catalogue_from_odoo(
    full_resync: bool = False, trigger: str = "SCHEDULED", initiated_by: str = "celery-beat"
) -> dict[str, str]:
    with session_scope() as session:
        run = OdooCatalogueSyncService(session).sync_all(
            full_resync=full_resync,
            trigger=trigger,
            initiated_by=initiated_by,
            correlation_id=str(uuid.uuid4()),
        )
        run_id = str(run.id)
        status = run.status

    logger.info(
        "odoo_catalogue_sync_completed",
        extra={"run_id": run_id, "status": status, "full_resync": full_resync},
    )
    return {"run_id": run_id, "status": status}
