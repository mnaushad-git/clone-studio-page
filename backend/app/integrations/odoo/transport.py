"""Low-level Odoo JSON-RPC transport.

Owns the HTTP call, request-id generation, timeout, bounded retry/backoff, and
translation of every failure mode (network, timeout, malformed response, Odoo
application error) into the typed exceptions in exceptions.py. Nothing above this
module ever sees an httpx exception or a raw JSON-RPC envelope.

Protocol: Odoo's standard JSON-RPC external API (see docs/integrations/odoo-client.md
for why JSON-RPC over XML-RPC). One endpoint, `{base_url}/jsonrpc`, dispatching to an
Odoo "service" (`common`, `object`, `db`) and "method" within it, matching the same
service/method pairs XML-RPC's `/xmlrpc/2/common` and `/xmlrpc/2/object` expose.
"""

from __future__ import annotations

import itertools
import logging
import time
import uuid
from typing import Any, Protocol

import httpx

from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import (
    OdooConnectionError,
    OdooIntegrationError,
    OdooProtocolError,
    OdooRateLimitError,
    OdooRemoteError,
    OdooTimeoutError,
)

logger = logging.getLogger("app.integrations.odoo.transport")

# Odoo error `data.name` values that indicate a rate-limit-shaped condition on
# instances fronted by a proxy that enforces one. Odoo itself has no native concept
# of a 429; this is best-effort classification of what a fronting proxy might report
# via the same JSON-RPC error envelope.
_RATE_LIMIT_MARKERS = ("RateLimitExceeded", "TooManyRequests")


class SupportsHttpResponse(Protocol):
    """Structural response shape this module actually reads — matches httpx.Response
    without requiring one, so tests can substitute a plain fake.
    """

    status_code: int

    def json(self) -> Any: ...


class SupportsHttpPost(Protocol):
    """Minimal transport surface — lets tests substitute a fake without depending on
    httpx.Client's full interface.
    """

    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> SupportsHttpResponse: ...


class SupportsOdooCall(Protocol):
    """The surface OdooClient/OdooAuthenticator actually depend on — satisfied by
    OdooTransport and by any test double with a matching `.call()` method. Depending
    on this instead of the concrete OdooTransport class is what makes those two
    classes constructible with a mocked transport in tests (dependency injection).
    """

    def call(
        self,
        service: str,
        method: str,
        args: list[Any],
        *,
        retryable: bool = False,
        correlation_id: str | None = None,
    ) -> Any: ...


class OdooTransport:
    """Stateless, retryable JSON-RPC caller. One instance per OdooConfig; safe to
    share across a request/task lifetime (holds no session state — authentication.py
    owns the uid, not this class).
    """

    def __init__(self, config: OdooConfig, *, http_client: SupportsHttpPost | None = None) -> None:
        self._config = config
        self._http_client: SupportsHttpPost = http_client or httpx.Client(
            verify=config.verify_ssl,
        )
        self._request_ids = itertools.count(1)

    def close(self) -> None:
        if isinstance(self._http_client, httpx.Client):
            self._http_client.close()

    def __enter__(self) -> OdooTransport:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def call(
        self,
        service: str,
        method: str,
        args: list[Any],
        *,
        retryable: bool = False,
        correlation_id: str | None = None,
    ) -> Any:
        """Issue one JSON-RPC call. `retryable` gates the bounded-retry policy — only
        safe read operations should pass True (the client layer decides this, not the
        transport, since only the caller knows whether the operation is a read).
        """
        request_id = f"odoo_{uuid.uuid4().hex}"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
            "id": next(self._request_ids),
        }

        attempts = self._config.max_retries + 1 if retryable else 1
        last_exception: OdooIntegrationError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._call_once(payload, request_id, correlation_id, service, method)
            except (OdooConnectionError, OdooTimeoutError, OdooRateLimitError) as exc:
                last_exception = exc
                if attempt >= attempts:
                    raise
                backoff = self._config.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "odoo_transport_retry",
                    extra={
                        "correlation_id": correlation_id,
                        "odoo_request_id": request_id,
                        "service": service,
                        "method": method,
                        "attempt": attempt,
                        "max_attempts": attempts,
                        "backoff_seconds": backoff,
                        "reason": type(exc).__name__,
                    },
                )
                time.sleep(backoff)
        # Unreachable in practice — the loop always returns or raises — but keeps
        # mypy satisfied without a `# type: ignore`.
        assert last_exception is not None
        raise last_exception

    def _call_once(
        self,
        payload: dict[str, Any],
        request_id: str,
        correlation_id: str | None,
        service: str,
        method: str,
    ) -> Any:
        log_extra = {
            "correlation_id": correlation_id,
            "odoo_request_id": request_id,
            "service": service,
            "method": method,
        }
        try:
            response = self._http_client.post(
                self._config.jsonrpc_endpoint,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            logger.warning("odoo_transport_timeout", extra=log_extra)
            raise OdooTimeoutError(
                f"Odoo request timed out after {self._config.timeout_seconds}s "
                f"({service}.{method})",
                context={"service": service, "method": method},
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("odoo_transport_connection_error", extra=log_extra)
            raise OdooConnectionError(
                f"Could not reach Odoo at {self._config.base_url} ({service}.{method}): {exc}",
                context={"service": service, "method": method},
            ) from exc

        if response.status_code == 429:
            raise OdooRateLimitError(
                "Odoo (or a fronting proxy) rate-limited this request",
                context={"service": service, "method": method},
            )
        if response.status_code >= 500:
            raise OdooConnectionError(
                f"Odoo returned HTTP {response.status_code} ({service}.{method})",
                context={"service": service, "method": method, "status_code": response.status_code},
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise OdooProtocolError(
                f"Odoo response was not valid JSON ({service}.{method})",
                context={"service": service, "method": method},
            ) from exc

        if not isinstance(body, dict) or ("result" not in body and "error" not in body):
            raise OdooProtocolError(
                f"Odoo response did not match the JSON-RPC envelope ({service}.{method})",
                context={"service": service, "method": method},
            )

        if "error" in body:
            raise _error_from_jsonrpc_body(body["error"], service, method)

        logger.info("odoo_transport_call_succeeded", extra=log_extra)
        return body["result"]


def _error_from_jsonrpc_body(error: dict[str, Any], service: str, method: str) -> Exception:
    """Classification is deliberately conservative here: everything not clearly a
    rate-limit condition is surfaced as OdooRemoteError. authentication.py and
    client.py apply finer-grained classification for the error shapes they know how
    to distinguish (wrong credentials, access rights, validation, not-found) since
    that requires knowing which call was made, not just the raw error body.
    """
    data = error.get("data") if isinstance(error, dict) else None
    name = data.get("name") if isinstance(data, dict) else None
    message = error.get("message") if isinstance(error, dict) else "Odoo returned an error"
    context = {"service": service, "method": method, "odoo_error_name": name}

    if name in _RATE_LIMIT_MARKERS:
        return OdooRateLimitError(str(message), context=context)
    return OdooRemoteError(str(message), context=context)
