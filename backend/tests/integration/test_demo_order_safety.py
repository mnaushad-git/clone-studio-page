"""Stage A guarantees: demo orders stay out of Odoo, stubbed orders are never reported as
delivered, tracking tokens can't be guessed, and order.created has a defined lifecycle."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.dependencies import get_db
from app.integrations.odoo.order_push import OdooPushResult, StubOdooOrderPusher
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.scripts.requeue_stub_synced_orders import find_requeueable_orders, requeue_order
from app.services.checkout import odoo_sync_service, order_service
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
from tests.integration.test_odoo_sync_service import _create_and_pay_order
from tests.integration.test_orders_api import _checkout_payload, make_product_with_default_variant


class ExplodingPusher:
    """Stands in for the live pusher: the test fails if a demo order ever reaches it."""

    name = "live"

    def push_order(self, **_: Any) -> OdooPushResult:
        raise AssertionError("A demo order reached the Odoo pusher.")


class RecordingLivePusher:
    name = "live"

    def __init__(self) -> None:
        self.pushed: list[str] = []

    def push_order(self, *, order_number: str, **_: Any) -> OdooPushResult:
        self.pushed.append(order_number)
        return OdooPushResult(success=True, odoo_sale_order_id=4242, raw={})


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def demo_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(order_service, "get_settings", lambda: Settings(deployment_stage="demo"))


def _use_pusher(monkeypatch: pytest.MonkeyPatch, pusher: Any) -> None:
    monkeypatch.setattr(odoo_sync_service, "get_odoo_order_pusher", lambda _settings: pusher)


def _get_order(db_session: Session, order_id: str) -> Order:
    db_session.expire_all()
    order = db_session.get(Order, order_id)
    assert order is not None
    return order


def test_demo_stage_orders_are_marked_and_numbered_as_demo(
    api_client: TestClient, db_session: Session, demo_stage: None
) -> None:
    body = _create_and_pay_order(api_client, db_session)

    assert body["is_demo"] is True
    assert body["order_number"].startswith("DEMO-")
    assert _get_order(db_session, body["id"]).is_demo is True


def test_development_stage_orders_are_not_demo(api_client: TestClient, db_session: Session) -> None:
    body = _create_and_pay_order(api_client, db_session)

    assert body["is_demo"] is False
    assert body["order_number"].startswith("TB-")


def test_demo_order_never_reaches_the_pusher_even_when_live_is_selected(
    api_client: TestClient,
    db_session: Session,
    demo_stage: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _create_and_pay_order(api_client, db_session)
    _use_pusher(monkeypatch, ExplodingPusher())

    summary = OdooOrderSyncService(db_session).sync_paid_orders()

    assert summary.failed == 0
    order = _get_order(db_session, body["id"])
    assert order.odoo_sync_status == "simulated"
    assert order.odoo_sale_order_id is None
    assert order.odoo_last_synced_at is None


def test_stub_result_is_recorded_as_simulated_not_synced(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _create_and_pay_order(api_client, db_session)
    _use_pusher(monkeypatch, StubOdooOrderPusher())

    OdooOrderSyncService(db_session).sync_paid_orders()

    order = _get_order(db_session, body["id"])
    assert order.odoo_sync_status == "simulated"
    assert order.odoo_last_synced_at is None


def test_real_push_is_recorded_as_synced(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _create_and_pay_order(api_client, db_session)
    pusher = RecordingLivePusher()
    _use_pusher(monkeypatch, pusher)

    OdooOrderSyncService(db_session).sync_paid_orders()

    order = _get_order(db_session, body["id"])
    assert pusher.pushed == [order.order_number]
    assert order.odoo_sync_status == "synced"
    assert order.odoo_sale_order_id == 4242


def test_requeue_includes_simulated_real_orders_but_never_demo_orders(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_pusher(monkeypatch, StubOdooOrderPusher())
    real = _create_and_pay_order(api_client, db_session)
    with monkeypatch.context() as stage:
        stage.setattr(order_service, "get_settings", lambda: Settings(deployment_stage="demo"))
        demo = _create_and_pay_order(api_client, db_session)
    OdooOrderSyncService(db_session).sync_paid_orders()
    db_session.expire_all()

    found = find_requeueable_orders(db_session)
    ids = {str(o.id) for o in found}
    assert real["id"] in ids
    assert demo["id"] not in ids

    for order in found:
        requeue_order(db_session, order)
    db_session.flush()

    # Moving to the live pusher now sends only the real order.
    pusher = RecordingLivePusher()
    _use_pusher(monkeypatch, pusher)
    OdooOrderSyncService(db_session).sync_paid_orders()

    assert pusher.pushed == [real["order_number"]]
    assert _get_order(db_session, demo["id"]).odoo_sync_status == "simulated"


def test_order_created_event_is_completed_and_has_no_backlog(
    api_client: TestClient, db_session: Session
) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    body = api_client.post("/api/v1/orders", json=_checkout_payload((product.slug, 1))).json()

    events = db_session.execute(
        select(OrderOutboxEvent).where(OrderOutboxEvent.order_id == body["id"])
    ).scalars()
    event = next(e for e in events if e.event_type == "order.created")
    assert event.status == "completed"
    assert event.processed_at is not None


def test_tracking_token_is_random_and_not_derived_from_the_order_number(
    api_client: TestClient, db_session: Session
) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    payload = _checkout_payload((product.slug, 1))
    first = api_client.post("/api/v1/orders", json=payload).json()
    second = api_client.post("/api/v1/orders", json=payload).json()

    assert first["tracking_token"].startswith("tk-")
    assert first["tracking_token"] != second["tracking_token"]
    assert len(first["tracking_token"]) >= 32
    derived = first["order_number"].lower().replace("-", "")
    assert derived not in first["tracking_token"].lower()
