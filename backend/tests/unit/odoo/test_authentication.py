from __future__ import annotations

import pytest

from app.integrations.odoo.authentication import OdooAuthenticator
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooAuthenticationError, OdooRemoteError
from tests.unit.odoo.conftest import FakeTransport


def test_get_server_version_parses_result(config: OdooConfig, transport: FakeTransport) -> None:
    transport.queue(
        ("common", "version"),
        {
            "server_version": "19.0",
            "server_version_info": [19, 0, 0, "final", 0, ""],
            "server_serie": "19.0",
            "protocol_version": 1,
        },
    )
    authenticator = OdooAuthenticator(config, transport)

    version = authenticator.get_server_version()

    assert version.server_version == "19.0"
    assert version.server_serie == "19.0"


def test_authenticate_succeeds_and_returns_session(
    config: OdooConfig, transport: FakeTransport
) -> None:
    transport.queue(("common", "authenticate"), 7)
    authenticator = OdooAuthenticator(config, transport)

    session = authenticator.authenticate()

    assert session.uid == 7
    assert session.database == config.database
    assert session.username == config.username


def test_authenticate_raises_on_falsy_uid(config: OdooConfig, transport: FakeTransport) -> None:
    transport.queue(("common", "authenticate"), False)
    authenticator = OdooAuthenticator(config, transport)

    with pytest.raises(OdooAuthenticationError):
        authenticator.authenticate()


def test_authenticate_wraps_remote_error(config: OdooConfig, transport: FakeTransport) -> None:
    transport.queue(("common", "authenticate"), OdooRemoteError("invalid database"))
    authenticator = OdooAuthenticator(config, transport)

    with pytest.raises(OdooAuthenticationError):
        authenticator.authenticate()


def test_authenticate_never_retries(config: OdooConfig, transport: FakeTransport) -> None:
    transport.queue(("common", "authenticate"), OdooRemoteError("bad credentials"))
    authenticator = OdooAuthenticator(config, transport)

    with pytest.raises(OdooAuthenticationError):
        authenticator.authenticate()

    call = transport.calls[0]
    assert call.retryable is False
