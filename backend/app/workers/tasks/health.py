"""Worker health tasks: a wiring smoke test and the heartbeat the health monitor reads."""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.services.ops.health_monitor import heartbeat_key
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.health.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="app.workers.tasks.health.record_heartbeat", ignore_result=True)
def record_heartbeat() -> None:
    # Only a task that Beat scheduled and a worker ran can write this, so a stale value
    # means one of the two has stopped.
    get_redis_client().set(heartbeat_key(get_settings()), str(time.time()), ex=86400)
