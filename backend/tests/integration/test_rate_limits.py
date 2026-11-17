"""Public endpoints are rate-limited per IP, and a Redis outage never blocks customers."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.core.config import Settings
from app.dependencies import get_db
from app.main import app
from tests.integration.test_orders_api import _checkout_payload, make_product_with_default_variant


class FakeRedis:
    def __init__(self, *, down: bool = False) -> None:
        self.counts: dict[str, int] = {}
        self.down = down

    def incr(self, key: str) -> int:
        if self.down:
            raise ConnectionError("down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> None:
        pass


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _limits(monkeypatch: pytest.MonkeyPatch, redis: FakeRedis, **overrides: Any) -> None:
    settings = Settings(rate_limit_enabled=True, **overrides)
    monkeypatch.setattr(rate_limit, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit, "get_redis_client", lambda: redis)


def test_order_creation_is_limited_per_ip(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(monkeypatch, FakeRedis(), rate_limit_order_create_per_10_min=3)
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    payload = _checkout_payload((product.slug, 1))

    codes = [api_client.post("/api/v1/orders", json=payload).status_code for _ in range(5)]

    assert codes == [200, 200, 200, 429, 429]
    body = api_client.post("/api/v1/orders", json=payload).json()
    assert body["error"]["code"] == "RATE_LIMITED"


def test_tracking_lookups_are_limited_per_ip(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(monkeypatch, FakeRedis(), rate_limit_order_lookup_per_minute=4)

    codes = [
        api_client.get(f"/api/v1/orders/by-tracking-token/tk-guess-{i}").status_code
        for i in range(6)
    ]

    assert codes == [404, 404, 404, 404, 429, 429]


def test_order_lookup_by_id_shares_the_lookup_limit(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(monkeypatch, FakeRedis(), rate_limit_order_lookup_per_minute=2)
    unknown = "00000000-0000-0000-0000-000000000000"

    codes = [
        api_client.get(f"/api/v1/orders/{unknown}").status_code,
        api_client.get("/api/v1/orders/by-tracking-token/tk-x").status_code,
        api_client.get(f"/api/v1/orders/{unknown}").status_code,
    ]

    assert codes == [404, 404, 429]


def test_payment_attempts_are_limited_per_ip(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(monkeypatch, FakeRedis(), rate_limit_order_pay_per_10_min=2)
    unknown = "00000000-0000-0000-0000-000000000000"

    codes = [
        api_client.post(f"/api/v1/orders/{unknown}/pay", json={"method_label": "x"}).status_code
        for _ in range(3)
    ]

    assert codes == [404, 404, 429]


def test_redis_outage_never_blocks_customers(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(monkeypatch, FakeRedis(down=True), rate_limit_order_create_per_10_min=1)
    product = make_product_with_default_variant(db_session, amount=Decimal("50.00"))
    payload = _checkout_payload((product.slug, 1))

    codes = [api_client.post("/api/v1/orders", json=payload).status_code for _ in range(3)]

    assert codes == [200, 200, 200]


def test_catalogue_browsing_is_not_limited(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _limits(
        monkeypatch,
        FakeRedis(),
        rate_limit_order_create_per_10_min=1,
        rate_limit_order_lookup_per_minute=1,
        rate_limit_order_pay_per_10_min=1,
    )

    codes = {api_client.get("/api/v1/catalogue/categories").status_code for _ in range(10)}

    assert 429 not in codes
