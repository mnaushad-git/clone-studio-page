"""Celery foundation: the app is importable/configured and a task runs in eager mode."""

from __future__ import annotations


def test_celery_app_is_configured_from_settings() -> None:
    from app.workers.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.broker_url
    assert celery_app.conf.result_backend


def test_ping_task_runs_synchronously_in_eager_mode() -> None:
    from app.workers.celery_app import celery_app
    from app.workers.tasks.health import ping

    celery_app.conf.task_always_eager = True
    result = ping.delay()

    assert result.get(timeout=5) == "pong"
