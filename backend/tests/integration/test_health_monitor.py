"""Operational health checks: they catch a stopped worker and a stalled order queue, and
their output carries no order or customer data."""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.dependencies import get_db
from app.main import app
from app.models.integration.odoo_catalogue_sync_run import OdooCatalogueSyncRun
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.services.ops.health_monitor import heartbeat_key, run_health_checks, summarize
from tests.integration.test_orders_api import _checkout_payload, make_product_with_default_variant

NOW = 1_800_000_000.0


class FakeRedis:
    def __init__(self, values: dict[str, Any] | None = None, *, down: bool = False) -> None:
        self.values = values or {}
        self.down = down

    def ping(self) -> bool:
        if self.down:
            raise ConnectionError("down")
        return True

    def get(self, name: str) -> Any:
        if self.down:
            raise ConnectionError("down")
        return self.values.get(name)


def _fresh_redis(age_seconds: float = 10) -> FakeRedis:
    return FakeRedis({heartbeat_key(get_settings()): str(NOW - age_seconds)})


def _by_name(checks: list[Any]) -> dict[str, Any]:
    return {c.name: c for c in checks}


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _sync_run(session: Session, *, started: datetime, error: str | None) -> None:
    session.add(
        OdooCatalogueSyncRun(
            trigger="MANUAL",
            status="FAILED" if error else "SUCCEEDED",
            started_at=started,
            correlation_id="corr",
            initiated_by="test",
            error_summary=error,
        )
    )
    session.flush()


def test_refused_price_publication_fails_its_check(db_session: Session) -> None:
    summary = "Catalogue not published. 1 of 55 differ"
    _sync_run(db_session, started=datetime.now(UTC), error=summary)

    checks = _by_name(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))

    assert not checks["catalogue_prices"].ok
    assert "55" not in checks["catalogue_prices"].detail


def test_check_recovers_after_a_good_sync_and_ignores_odoo_being_unconfigured(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    _sync_run(db_session, started=now - timedelta(minutes=10), error="Catalogue not published. x")
    _sync_run(db_session, started=now - timedelta(minutes=5), error=None)
    assert _by_name(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))[
        "catalogue_prices"
    ].ok

    _sync_run(db_session, started=now, error="Odoo is not configured")
    assert _by_name(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))[
        "catalogue_prices"
    ].ok


def test_infrastructure_checks_pass_with_a_fresh_heartbeat(db_session: Session) -> None:
    checks = _by_name(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))

    assert checks["database"].ok
    assert checks["redis"].ok
    assert checks["worker_heartbeat"].ok


def test_missing_heartbeat_fails(db_session: Session) -> None:
    checks = _by_name(run_health_checks(db_session, FakeRedis(), get_settings(), now=NOW))

    assert not checks["worker_heartbeat"].ok
    assert "not running" in checks["worker_heartbeat"].detail


def test_stale_heartbeat_fails(db_session: Session) -> None:
    settings = get_settings()
    redis_client = _fresh_redis(settings.ops_heartbeat_max_age_seconds + 60)

    checks = _by_name(run_health_checks(db_session, redis_client, settings, now=NOW))

    assert not checks["worker_heartbeat"].ok


def test_redis_down_is_reported_not_raised(db_session: Session) -> None:
    checks = _by_name(run_health_checks(db_session, FakeRedis(down=True), get_settings(), now=NOW))

    assert not checks["redis"].ok
    assert not checks["worker_heartbeat"].ok


def _pay(api_client: TestClient, db_session: Session) -> dict[str, Any]:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    created = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1))).json()
    paid = api_client.post(f"/api/v1/orders/{created['id']}/pay", json={"method_label": "Test"})
    return paid.json()


def _age_events(db_session: Session, order_id: str, minutes: int) -> None:
    db_session.execute(
        update(OrderOutboxEvent)
        .where(OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.status == "pending")
        .values(created_at=datetime.now(UTC) - timedelta(minutes=minutes))
    )
    db_session.flush()


def test_stalled_paid_order_fails_the_queue_check(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.orders.push_paid_orders_to_odoo.delay", lambda: None)
    monkeypatch.setattr("app.api.v1.endpoints.orders.send_order_confirmations.delay", lambda: None)
    settings = get_settings()
    order = _pay(api_client, db_session)
    _age_events(db_session, order["id"], settings.ops_outbox_max_age_minutes + 5)

    checks = _by_name(run_health_checks(db_session, _fresh_redis(), settings, now=NOW))

    assert not checks["order_queue"].ok


def test_order_created_events_never_count_as_backlog(
    api_client: TestClient, db_session: Session
) -> None:
    settings = get_settings()
    before = _by_name(run_health_checks(db_session, _fresh_redis(), settings, now=NOW))
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    body = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1))).json()
    db_session.execute(
        update(OrderOutboxEvent)
        .where(OrderOutboxEvent.order_id == body["id"])
        .values(created_at=datetime.now(UTC) - timedelta(days=30), status="pending")
    )
    db_session.flush()

    after = _by_name(run_health_checks(db_session, _fresh_redis(), settings, now=NOW))

    assert after["order_queue"].detail == before["order_queue"].detail


def test_failed_event_fails_the_failures_check(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.orders.push_paid_orders_to_odoo.delay", lambda: None)
    monkeypatch.setattr("app.api.v1.endpoints.orders.send_order_confirmations.delay", lambda: None)
    order = _pay(api_client, db_session)
    event = db_session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order["id"], OrderOutboxEvent.event_type == "order.paid"
        )
    ).scalar_one()
    event.status = "failed"
    db_session.flush()

    checks = _by_name(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))

    assert not checks["order_failures"].ok


def test_summary_contains_no_order_or_customer_data(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.orders.push_paid_orders_to_odoo.delay", lambda: None)
    monkeypatch.setattr("app.api.v1.endpoints.orders.send_order_confirmations.delay", lambda: None)
    order = _pay(api_client, db_session)

    output = json.dumps(
        summarize(run_health_checks(db_session, _fresh_redis(), get_settings(), now=NOW))
    )

    assert order["order_number"] not in output
    assert order["recipient_name"] not in output
    assert order["recipient_phone"] not in output


def test_heartbeat_task_writes_a_current_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.workers.tasks import health

    written: dict[str, Any] = {}

    class Recorder:
        def set(self, name: str, value: str, ex: int) -> None:
            written[name] = value

    monkeypatch.setattr(health, "get_redis_client", lambda: Recorder())

    health.record_heartbeat()

    value = float(written[heartbeat_key(get_settings())])
    assert abs(value - time.time()) < 5
