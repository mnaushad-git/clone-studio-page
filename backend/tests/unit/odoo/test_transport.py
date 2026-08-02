from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import (
    OdooConnectionError,
    OdooProtocolError,
    OdooRateLimitError,
    OdooRemoteError,
    OdooTimeoutError,
)
from app.integrations.odoo.transport import OdooTransport
from tests.unit.odoo.conftest import make_config


class FakeHttpResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload


class FakeHttpClient:
    """Queue of responses/exceptions returned in order, one per `.post()` call."""

    def __init__(self, sequence: list[Any]) -> None:
        self._sequence = list(sequence)
        self.call_count = 0

    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> FakeHttpResponse:
        self.call_count += 1
        item = self._sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def config() -> OdooConfig:
    return make_config(max_retries=2, retry_backoff_seconds=0.0)


def test_call_returns_result_on_success(config: OdooConfig) -> None:
    http_client = FakeHttpClient(
        [FakeHttpResponse(200, {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})]
    )
    transport = OdooTransport(config, http_client=http_client)

    result = transport.call("common", "version", [])

    assert result == {"ok": True}


def test_call_raises_timeout_error_on_httpx_timeout(config: OdooConfig) -> None:
    http_client = FakeHttpClient([httpx.TimeoutException("timed out")])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooTimeoutError):
        transport.call("common", "version", [])


def test_call_raises_connection_error_on_httpx_error(config: OdooConfig) -> None:
    http_client = FakeHttpClient([httpx.ConnectError("refused")])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooConnectionError):
        transport.call("common", "version", [])


def test_call_raises_connection_error_on_5xx(config: OdooConfig) -> None:
    http_client = FakeHttpClient([FakeHttpResponse(502)])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooConnectionError):
        transport.call("common", "version", [])


def test_call_raises_rate_limit_error_on_429(config: OdooConfig) -> None:
    http_client = FakeHttpClient([FakeHttpResponse(429)])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooRateLimitError):
        transport.call("common", "version", [])


def test_call_raises_protocol_error_on_malformed_json(config: OdooConfig) -> None:
    http_client = FakeHttpClient([FakeHttpResponse(200, None)])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooProtocolError):
        transport.call("common", "version", [])


def test_call_raises_protocol_error_on_unexpected_envelope(config: OdooConfig) -> None:
    http_client = FakeHttpClient([FakeHttpResponse(200, {"unexpected": "shape"})])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooProtocolError):
        transport.call("common", "version", [])


def test_call_raises_remote_error_on_jsonrpc_error_body(config: OdooConfig) -> None:
    http_client = FakeHttpClient(
        [
            FakeHttpResponse(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"message": "boom", "data": {"name": "SomeError"}},
                },
            )
        ]
    )
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooRemoteError, match="boom"):
        transport.call("common", "version", [])


def test_non_retryable_call_does_not_retry_on_failure(config: OdooConfig) -> None:
    http_client = FakeHttpClient([httpx.ConnectError("refused")])
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooConnectionError):
        transport.call("common", "version", [], retryable=False)

    assert http_client.call_count == 1


def test_retryable_call_retries_up_to_max_retries_then_raises(config: OdooConfig) -> None:
    # max_retries=2 -> 3 total attempts
    http_client = FakeHttpClient(
        [httpx.ConnectError("1"), httpx.ConnectError("2"), httpx.ConnectError("3")]
    )
    transport = OdooTransport(config, http_client=http_client)

    with pytest.raises(OdooConnectionError):
        transport.call("common", "version", [], retryable=True)

    assert http_client.call_count == 3


def test_retryable_call_succeeds_after_transient_failure(config: OdooConfig) -> None:
    http_client = FakeHttpClient(
        [
            httpx.ConnectError("transient"),
            FakeHttpResponse(200, {"jsonrpc": "2.0", "id": 1, "result": 42}),
        ]
    )
    transport = OdooTransport(config, http_client=http_client)

    result = transport.call("common", "version", [], retryable=True)

    assert result == 42
    assert http_client.call_count == 2
