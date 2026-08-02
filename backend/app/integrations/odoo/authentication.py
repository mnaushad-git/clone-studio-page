"""Odoo authentication — the `common` JSON-RPC service.

Never logs a password or API key: only OdooConfig.masked_dict()-shaped data and the
resulting uid (an integer, not a secret) are ever passed to the logger.
"""

from __future__ import annotations

import logging

from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooAuthenticationError, OdooRemoteError
from app.integrations.odoo.models import OdooServerVersion, OdooSession
from app.integrations.odoo.transport import SupportsOdooCall

logger = logging.getLogger("app.integrations.odoo.authentication")


class OdooAuthenticator:
    """Wraps the `common.authenticate`/`common.version` JSON-RPC calls. Holds no
    session state itself — callers (client.py) own the resulting OdooSession.
    """

    def __init__(self, config: OdooConfig, transport: SupportsOdooCall) -> None:
        self._config = config
        self._transport = transport

    def get_server_version(self, *, correlation_id: str | None = None) -> OdooServerVersion:
        result = self._transport.call(
            "common", "version", [], retryable=True, correlation_id=correlation_id
        )
        return OdooServerVersion(
            server_version=result.get("server_version", ""),
            server_version_info=list(result.get("server_version_info", [])),
            server_serie=result.get("server_serie", ""),
            protocol_version=int(result.get("protocol_version", 0)),
        )

    def authenticate(self, *, correlation_id: str | None = None) -> OdooSession:
        """Logs in and returns the resulting uid. Never retried automatically — a bad
        credential fails the same way every time, so a retry only delays surfacing a
        real configuration problem.
        """
        try:
            uid = self._transport.call(
                "common",
                "authenticate",
                [self._config.database, self._config.username, self._config.credential, {}],
                retryable=False,
                correlation_id=correlation_id,
            )
        except OdooRemoteError as exc:
            raise OdooAuthenticationError(
                f"Odoo authentication failed for database={self._config.database!r} "
                f"username={self._config.username!r}",
                context={"database": self._config.database, "username": self._config.username},
            ) from exc

        if not uid:
            raise OdooAuthenticationError(
                f"Odoo rejected the credential for database={self._config.database!r} "
                f"username={self._config.username!r} (authenticate returned no uid)",
                context={"database": self._config.database, "username": self._config.username},
            )

        logger.info(
            "odoo_authentication_succeeded",
            extra={"correlation_id": correlation_id, "database": self._config.database, "uid": uid},
        )
        return OdooSession(
            uid=int(uid), database=self._config.database, username=self._config.username
        )
