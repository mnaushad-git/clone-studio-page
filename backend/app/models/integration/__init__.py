"""Integration/sync metadata models: checkpoints for future sync jobs and catalogue
seed-run history. No sync jobs are implemented this phase — these tables exist so
future workers have somewhere auditable to write to.
"""

from __future__ import annotations

from app.models.integration.odoo_catalogue_sync_item import OdooCatalogueSyncItem
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.models.integration.odoo_import_item import OdooCatalogueImportItem
from app.models.integration.odoo_import_run import OdooCatalogueImportRun
from app.models.integration.seed_run import CatalogueSeedRun
from app.models.integration.sync_checkpoint import IntegrationSyncCheckpoint

__all__ = [
    "CatalogueSeedRun",
    "IntegrationSyncCheckpoint",
    "OdooCatalogueImportItem",
    "OdooCatalogueImportRun",
    "OdooCatalogueSyncItem",
    "OdooCatalogueSyncRun",
]
