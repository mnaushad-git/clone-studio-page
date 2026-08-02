"""Foundation smoke-test task — proves worker/broker/result-backend wiring works."""

from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.health.ping")
def ping() -> str:
    return "pong"
