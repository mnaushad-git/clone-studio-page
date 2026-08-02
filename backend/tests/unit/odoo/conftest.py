"""Shared fixtures for the Odoo integration test suite.

Nothing here touches a network or a real Odoo instance — FakeTransport implements
the same `.call(service, method, args, *, retryable, correlation_id)` surface
OdooTransport exposes, so OdooClient/OdooAuthenticator/repositories/discovery can all
be exercised without httpx ever being involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig


@dataclass
class RecordedCall:
    service: str
    method: str
    args: list[Any]
    retryable: bool
    correlation_id: str | None


class FakeTransport:
    """A response queued once is treated as a fixed/repeatable value (returned on
    every subsequent call with the same key) — matches how real code re-issues the
    same read (e.g. fields_get on the same model) many times. Queue the same key
    twice to get sequenced values instead (used for pagination tests): each extra
    call consumes one, until exactly one value is left, which then repeats.
    """

    def __init__(self) -> None:
        self.calls: list[RecordedCall] = []
        self._responses: dict[tuple[Any, ...], list[Any]] = {}

    @staticmethod
    def _key_for(service: str, method: str, args: list[Any]) -> tuple[Any, ...]:
        if service == "object" and method == "execute_kw":
            model = args[3]
            odoo_method = args[4]
            return ("execute_kw", model, odoo_method)
        return (service, method)

    def queue(self, key: tuple[Any, ...], value: Any) -> None:
        self._responses.setdefault(key, []).append(value)

    def call(
        self,
        service: str,
        method: str,
        args: list[Any],
        *,
        retryable: bool = False,
        correlation_id: str | None = None,
    ) -> Any:
        self.calls.append(RecordedCall(service, method, args, retryable, correlation_id))
        key = self._key_for(service, method, args)
        queued = self._responses.get(key)
        if not queued:
            raise AssertionError(f"FakeTransport: no response queued for {key}")
        value = queued.pop(0) if len(queued) > 1 else queued[0]
        if isinstance(value, BaseException):
            raise value
        return value

    def write_call_count(self) -> int:
        write_methods = {"create", "write", "unlink", "copy", "action_archive", "action_unarchive"}
        return sum(
            1
            for c in self.calls
            if c.service == "object" and c.method == "execute_kw" and c.args[4] in write_methods
        )


def make_config(**overrides: Any) -> OdooConfig:
    defaults: dict[str, Any] = {
        "base_url": "http://localhost:8069",
        "database": "terrific_bites_dev",
        "username": "admin",
        "password": "admin-password",  # noqa: S106 - test fixture value, not a real secret
        "api_key": None,
        "timeout_seconds": 30.0,
        "verify_ssl": True,
        "max_retries": 2,
        "retry_backoff_seconds": 0.0,
        "read_batch_size": 5,
        "protocol": "jsonrpc",
        "company_id": None,
        "default_pricelist_id": None,
        "default_warehouse_id": None,
    }
    defaults.update(overrides)
    return OdooConfig(**defaults)


@pytest.fixture
def config() -> OdooConfig:
    return make_config()


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def client(config: OdooConfig, transport: FakeTransport) -> OdooClient:
    return OdooClient(config, transport)


@pytest.fixture
def authenticated_client(client: OdooClient, transport: FakeTransport) -> OdooClient:
    transport.queue(("common", "authenticate"), 7)
    client.authenticate()
    return client
