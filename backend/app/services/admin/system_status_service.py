"""Operational status for the Admin Portal's system-status screen and banner (task
brief §9). Deliberately never makes a live synchronous call to Odoo from inside this
request handler (CLAUDE.md rule 5: "Long-running or synchronous-to-Odoo work happens
in background workers, never inside a FastAPI request handler") — Odoo status is
"configured"/"not_configured" based on settings presence only, not a live ping.
Celery worker/beat detection is a best-effort, short-timeout broker inspection; its
own unavailability must never make this endpoint slow or fail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.cache import metrics as cache_metrics
from app.cache.keys import CACHE_KEY_VERSION
from app.core.config import Settings, get_settings
from app.core.database import check_database_connection
from app.core.redis import check_redis_connection
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.services.admin.system_status")


@dataclass(frozen=True)
class SystemStatus:
    database: str
    redis: str
    celery_worker: str
    celery_beat: str
    odoo: str
    payment_provider_mode: str
    notification_provider_mode: str
    odoo_order_push_mode: str
    cache_enabled: bool
    cache_key_version: str
    cache_hits: int
    cache_misses: int
    cache_errors: int


def _celery_worker_status() -> str:
    try:
        replies = celery_app.control.inspect(timeout=1.0).ping()
        return "up" if replies else "down"
    except Exception:  # noqa: BLE001 - broker unreachable must degrade, never 500
        logger.warning("celery_worker_status_check_failed")
        return "down"


def _celery_beat_status(worker_up: str) -> str:
    # Celery has no direct "is Beat running" probe short of checking its schedule
    # file/heartbeat, which isn't exposed here — if the broker itself is unreachable,
    # Beat can't be reachable either; otherwise we honestly don't know from this
    # request alone.
    return "down" if worker_up == "down" else "unknown"


def _odoo_status(settings: Settings) -> str:
    return "configured" if settings.odoo_base_url and settings.odoo_database else "not_configured"


def get_system_status() -> SystemStatus:
    settings = get_settings()
    database = "up" if check_database_connection() else "down"
    redis = "up" if check_redis_connection() else "down"
    celery_worker = _celery_worker_status()
    celery_beat = _celery_beat_status(celery_worker)
    cache_snapshot = cache_metrics.snapshot()

    return SystemStatus(
        database=database,
        redis=redis,
        celery_worker=celery_worker,
        celery_beat=celery_beat,
        odoo=_odoo_status(settings),
        payment_provider_mode=settings.payment_provider,
        notification_provider_mode=settings.notification_provider,
        odoo_order_push_mode=settings.odoo_order_push_provider,
        cache_enabled=settings.cache_enabled,
        cache_key_version=CACHE_KEY_VERSION,
        cache_hits=cache_snapshot.hits,
        cache_misses=cache_snapshot.misses,
        cache_errors=cache_snapshot.errors,
    )
