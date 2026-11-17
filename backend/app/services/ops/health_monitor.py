"""Operational health checks, run by app/scripts/ops_health_check.py and alerted on by
deploy/scripts/monitor.sh. Goes further than /readiness, which only proves the API can
reach PostgreSQL and Redis: this also notices a stopped worker or a stalled order queue.

Reports counts and ages only, never order or customer data, because the output is sent to
an alert channel.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.services.catalogue.variant_pricing import CATALOGUE_NOT_PUBLISHED

# order.created is excluded: it is an audit record with no consumer.
_CONSUMED_EVENT_TYPES = ("order.paid", "order.notify")


class RedisLike(Protocol):
    def ping(self) -> Any: ...

    def get(self, name: str) -> Any: ...


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str


def heartbeat_key(settings: Settings) -> str:
    return f"{settings.cache_key_prefix}:ops:worker_heartbeat"


def _check_database(session: Session) -> HealthCheck:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure is the result being reported
        return HealthCheck("database", False, f"unreachable ({type(exc).__name__})")
    return HealthCheck("database", True, "reachable")


def _check_redis(redis_client: RedisLike) -> HealthCheck:
    try:
        redis_client.ping()
    except Exception as exc:  # noqa: BLE001 - any failure is the result being reported
        return HealthCheck("redis", False, f"unreachable ({type(exc).__name__})")
    return HealthCheck("redis", True, "reachable")


def _check_heartbeat(redis_client: RedisLike, settings: Settings, now: float) -> HealthCheck:
    try:
        raw = redis_client.get(heartbeat_key(settings))
    except Exception as exc:  # noqa: BLE001 - any failure is the result being reported
        return HealthCheck("worker_heartbeat", False, f"unreadable ({type(exc).__name__})")
    if raw is None:
        return HealthCheck("worker_heartbeat", False, "never recorded: worker or Beat not running")
    age = int(now - float(raw))
    limit = settings.ops_heartbeat_max_age_seconds
    if age > limit:
        return HealthCheck("worker_heartbeat", False, f"{age}s old, limit {limit}s")
    return HealthCheck("worker_heartbeat", True, f"{age}s old")


def _check_outbox(session: Session, settings: Settings) -> list[HealthCheck]:
    outbox = OrderOutboxRepository(session)
    minutes = settings.ops_outbox_max_age_minutes
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    try:
        stale = outbox.count_pending_older_than(_CONSUMED_EVENT_TYPES, cutoff)
        failed = sum(
            outbox.count_by_type_and_status(event_type, status)
            for event_type in _CONSUMED_EVENT_TYPES
            for status in ("failed", "dead_letter")
        )
    except Exception as exc:  # noqa: BLE001 - any failure is the result being reported
        return [HealthCheck("order_queue", False, f"unreadable ({type(exc).__name__})")]
    return [
        HealthCheck("order_queue", stale == 0, f"{stale} pending over {minutes} min"),
        HealthCheck("order_failures", failed == 0, f"{failed} failed events"),
    ]


def _check_catalogue_prices(session: Session) -> HealthCheck:
    latest = (
        select(OdooCatalogueSyncRun.error_summary)
        .where(OdooCatalogueSyncRun.status != "RUNNING")
        .order_by(OdooCatalogueSyncRun.started_at.desc())
        .limit(1)
    )
    try:
        summary = session.execute(latest).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - any failure is the result being reported
        return HealthCheck("catalogue_prices", False, f"unreadable ({type(exc).__name__})")
    if summary and summary.startswith(CATALOGUE_NOT_PUBLISHED):
        return HealthCheck(
            "catalogue_prices", False, "latest sync refused: see Admin, catalogue sync runs"
        )
    return HealthCheck("catalogue_prices", True, "latest sync not refused")


def run_health_checks(
    session: Session,
    redis_client: RedisLike,
    settings: Settings,
    *,
    now: float | None = None,
) -> list[HealthCheck]:
    current = time.time() if now is None else now
    return [
        _check_database(session),
        _check_redis(redis_client),
        _check_heartbeat(redis_client, settings, current),
        *_check_outbox(session, settings),
        _check_catalogue_prices(session),
    ]


def summarize(checks: list[HealthCheck]) -> dict[str, Any]:
    return {
        "status": "ok" if all(c.ok for c in checks) else "failing",
        "checks": [asdict(c) for c in checks],
    }
