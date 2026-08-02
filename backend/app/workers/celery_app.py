"""Celery application foundation, shared by the worker and beat scheduler processes."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "terrific_bites",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.health",
        "app.workers.tasks.order_sync",
        "app.workers.tasks.order_notifications",
        "app.workers.tasks.catalogue_sync",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # A request handler that calls .delay() (e.g. POST /orders/{id}/pay, which fires
    # two independent nudges — Odoo sync and notifications) must never block on a
    # slow/unreachable broker — Celery's defaults (4s connect timeout, up to 3 publish
    # retries with backoff) can add 10+ seconds *per call* to a customer-facing payment
    # response. Fail fast instead: one short-timeout attempt, no retries, per call. The
    # caller's try/except treats any failure as "the periodic Beat poll will pick this
    # up instead" (see beat_schedule below), never as a request-blocking condition.
    broker_connection_timeout=0.3,
    task_publish_retry=False,
    # broker_connection_timeout alone doesn't bound the underlying redis-py socket —
    # these do (confirmed by measuring an unreachable-broker .delay() call: without
    # these it took 4+ seconds even with the settings above).
    broker_transport_options={"socket_connect_timeout": 0.3, "socket_timeout": 0.3},
    # Belt-and-suspenders with the /orders/{id}/pay endpoint's post-commit .delay()
    # nudge: this periodic poll is what actually guarantees a paid order gets pushed
    # even if that nudge is lost (worker down, broker hiccup) — the outbox event just
    # stays `pending` until the next tick picks it up.
    beat_schedule={
        "push-paid-orders-to-odoo": {
            "task": "app.workers.tasks.order_sync.push_paid_orders_to_odoo",
            "schedule": 60.0,
        },
        # Shorter interval than the Odoo push: a delayed order confirmation is a
        # customer-visible UX problem (did my payment even go through?), a delayed
        # Odoo sync isn't.
        "send-order-confirmations": {
            "task": "app.workers.tasks.order_notifications.send_order_confirmations",
            "schedule": 30.0,
        },
        # Products flow Odoo -> background worker -> PostgreSQL (CLAUDE.md rule 4);
        # this is the pull side. Interval is config-driven (ODOO_CATALOGUE_SYNC_
        # INTERVAL_SECONDS, default 300s) rather than hardcoded like the two schedules
        # above, since how often a bakery's Odoo catalogue actually changes is an
        # operational tuning knob, not a fixed architectural constant.
        "sync-catalogue-from-odoo": {
            "task": "app.workers.tasks.catalogue_sync.sync_catalogue_from_odoo",
            "schedule": settings.odoo_catalogue_sync_interval_seconds,
        },
    },
)
