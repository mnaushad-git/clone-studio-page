"""Proves CLAUDE.md rule 8 under failure, not just the happy path: if anything fails
between the order row and its outbox event being written, NEITHER persists. Without
this, test_create_order_writes_order_and_outbox_event_in_one_transaction (in
test_orders_api.py) only shows they're written together when nothing goes wrong.
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.main import app
from app.models.orders.order import Order
from app.models.orders.order_outbox_event import OrderOutboxEvent
from app.repositories.orders.order_outbox_repository import OrderOutboxRepository
from tests.integration.catalogue_factories import make_product_with_default_variant


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        # raise_server_exceptions=False: Starlette's ServerErrorMiddleware re-raises
        # the original exception in-process after sending the 500 response (so it
        # surfaces in server logs) — the default TestClient propagates that into the
        # test itself. This test wants the actual JSON error response, not the raise.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _order_count(session: Session) -> int:
    return session.execute(select(func.count()).select_from(Order)).scalar_one()


def test_a_failure_after_order_creation_leaves_neither_order_nor_outbox_event(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    orders_before = _order_count(db_session)

    def _boom(self: OrderOutboxRepository, obj: OrderOutboxEvent) -> OrderOutboxEvent:
        raise RuntimeError("simulated failure writing the outbox event")

    monkeypatch.setattr(OrderOutboxRepository, "create", _boom)

    response = api_client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_slug": product.slug, "quantity": 1}],
            "promo_code": None,
            "customer": {"name": "Sara M.", "phone": "+966500000000"},
            "delivery": {
                "is_gift": False,
                "recipient_name": "Sara M.",
                "recipient_phone": "+966500000000",
                "area": "Al Olaya",
                "address": "123 Test Street",
            },
        },
    )

    assert response.status_code == 500

    # The endpoint's session.commit() never ran (the exception was raised before it),
    # and get_db()'s finally-close rolls back whatever the request left pending — so
    # nothing from this attempt should be visible, not even a half-created order.
    db_session.rollback()
    assert _order_count(db_session) == orders_before
    orphaned_events = db_session.execute(select(OrderOutboxEvent)).scalars().all()
    assert orphaned_events == []
