"""Worker reliability against a real PostgreSQL: retries, backoff, dead-lettering, and the
row lock that stops two workers pushing one order."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.integrations.odoo.order_push import OdooPushResult
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from app.services.checkout import odoo_sync_service as sync_module
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
from tests.integration.catalogue_factories import make_product_with_default_variant


class _ScriptedPusher:
    name = "live"

    def __init__(self, *results: bool) -> None:
        self.results = list(results)
        self.calls = 0

    def push_order(self, **_: Any) -> OdooPushResult:
        self.calls += 1
        ok = self.results.pop(0)
        return OdooPushResult(success=ok, odoo_sale_order_id=900 if ok else None, raw={})


def _use(monkeypatch: pytest.MonkeyPatch, pusher: _ScriptedPusher) -> None:
    monkeypatch.setattr(sync_module, "get_odoo_order_pusher", lambda settings: pusher)


def _api(session: Session) -> Generator[TestClient, None, None]:
    def _override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = _override
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _api(db_session)


def _paid_order(client: TestClient, session: Session) -> str:
    product = make_product_with_default_variant(session, amount=Decimal("50.00"))
    contact = {"name": "Sara", "phone": "+966500000000"}
    created = client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": None,
            "customer": contact,
            "delivery": {
                "is_gift": False,
                "recipient_name": contact["name"],
                "recipient_phone": contact["phone"],
                "area": "Al Olaya",
                "address": "123 Test Street",
            },
        },
    ).json()
    client.post(f"/api/v1/orders/{created['id']}/pay", json={"method_label": "Cash"})
    return created["id"]


def _event(session: Session, order_id: str) -> OrderOutboxEvent:
    return session.execute(
        select(OrderOutboxEvent).where(
            OrderOutboxEvent.order_id == order_id, OrderOutboxEvent.event_type == "order.paid"
        )
    ).scalar_one()


def test_a_failure_schedules_a_retry_outside_the_odoo_timeout(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order_id = _paid_order(api_client, db_session)
    pusher = _ScriptedPusher(False)
    _use(monkeypatch, pusher)
    service = OdooOrderSyncService(db_session)

    service.sync_paid_orders()

    event = _event(db_session, order_id)
    assert event.status == "failed"
    assert event.next_attempt_at is not None
    wait = event.next_attempt_at - datetime.now(UTC)
    assert wait > timedelta(seconds=2 * service.settings.odoo_timeout_seconds - 5)

    # Not due yet, so a second poll doesn't touch it.
    assert service.sync_paid_orders().processed == 0
    assert pusher.calls == 1


def test_the_retry_delay_doubles_and_is_capped(db_session: Session) -> None:
    service = OdooOrderSyncService(db_session)
    service.settings = service.settings.model_copy(
        update={
            "order_sync_retry_base_seconds": 120,
            "order_sync_retry_max_seconds": 400,
            "odoo_timeout_seconds": 30,
        }
    )

    delays = [service._retry_delay(n).total_seconds() for n in (1, 2, 3)]  # noqa: SLF001

    assert delays == [120, 240, 400]


def test_a_due_retry_succeeds_and_clears_the_failure(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order_id = _paid_order(api_client, db_session)
    _use(monkeypatch, _ScriptedPusher(False, True))
    service = OdooOrderSyncService(db_session)
    service.sync_paid_orders()
    event = _event(db_session, order_id)
    event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    assert service.sync_paid_orders().succeeded == 1

    event = _event(db_session, order_id)
    assert (event.status, event.attempts, event.next_attempt_at) == ("completed", 1, None)
    order = db_session.get(Order, order_id)
    assert order is not None
    assert (order.odoo_sync_status, order.odoo_sale_order_id) == ("synced", 900)


def test_retries_end_in_the_dead_letter_state_until_an_operator_acts(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    order_id = _paid_order(api_client, db_session)
    pusher = _ScriptedPusher(False, False)
    _use(monkeypatch, pusher)
    service = OdooOrderSyncService(db_session)
    service.settings = service.settings.model_copy(update={"order_sync_max_attempts": 2})

    service.sync_paid_orders()
    event = _event(db_session, order_id)
    event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()
    service.sync_paid_orders()

    event = _event(db_session, order_id)
    assert (event.status, event.attempts, event.next_attempt_at) == ("dead_letter", 2, None)
    assert service.sync_paid_orders().processed == 0
    assert pusher.calls == 2


def test_a_second_worker_cannot_claim_an_event_and_a_crash_releases_it(
    db_engine: Engine, flush_cache: None
) -> None:
    """Needs two real connections and committed rows, so it can't use db_session."""
    setup = Session(db_engine)
    first = Session(db_engine)
    second = Session(db_engine)
    try:
        for client in _api(setup):
            order_id = _paid_order(client, setup)
        # Eager Celery has already run the stub sync for this committed order.
        _event(setup, order_id).status = "pending"
        setup.commit()
        now = datetime.now(UTC) + timedelta(seconds=1)

        claimed = OrderOutboxRepository(first).claim_next_due("order.paid", now)
        assert claimed is not None
        assert str(claimed.order_id) == order_id

        assert OrderOutboxRepository(second).claim_next_due("order.paid", now) is None
        second.rollback()

        # A worker dying ends its transaction exactly as this does.
        first.rollback()
        reclaimed = OrderOutboxRepository(second).claim_next_due("order.paid", now)
        assert reclaimed is not None
        assert reclaimed.status == "pending"
    finally:
        first.close()
        second.close()
        setup.rollback()
        setup.execute(
            text("TRUNCATE orders, catalogue_products, catalogue_categories CASCADE")
        )
        setup.commit()
        setup.close()
