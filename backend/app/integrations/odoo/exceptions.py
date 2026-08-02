"""Stable Odoo integration exception hierarchy.

Every failure mode the adapter can encounter (config, network, auth, protocol,
remote application errors) is converted to one of these before it leaves
app/integrations/odoo/ — no other module ever catches an httpx exception, an
xmlrpc.client.Fault, or parses a raw Odoo error dict (integration-principles.md
§1: "nothing outside integrations/odoo/ ... parses an Odoo response shape").

None of these carry the raw request/response payload by default, since that could
contain a session id or echoed credential; callers that need the underlying detail
for logging use `.safe_context()`, which is pre-redacted.
"""

from __future__ import annotations

from typing import Any


class OdooIntegrationError(Exception):
    """Base class for every exception raised by app/integrations/odoo/."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self._context = context or {}

    def safe_context(self) -> dict[str, Any]:
        """Context dict safe to attach to a structured log record — never includes a
        password, api key, session id, or raw authentication payload (callers must
        not add those keys to `context` in the first place; this is the second line
        of defense, not the only one).
        """
        redacted_keys = {"password", "api_key", "session_id", "auth_payload", "cookie"}
        return {k: v for k, v in self._context.items() if k not in redacted_keys}


class OdooConfigurationError(OdooIntegrationError):
    """Configuration is missing, malformed, or internally inconsistent
    (e.g. neither password nor api key set, an unparsable base URL, a
    non-positive timeout). Raised at client construction time — fail fast,
    never at first use.
    """


class OdooConnectionError(OdooIntegrationError):
    """The Odoo server could not be reached at the transport level (DNS, TCP
    refused, TLS failure). Distinct from OdooTimeoutError.
    """


class OdooTimeoutError(OdooIntegrationError):
    """The request exceeded ODOO_TIMEOUT_SECONDS. Safe to retry for read-only
    operations, per the bounded-retry policy in transport.py.
    """


class OdooProtocolError(OdooIntegrationError):
    """The response did not conform to the expected JSON-RPC/XML-RPC envelope
    (malformed JSON, unexpected shape, HTTP status outside 2xx/4xx/5xx handled
    explicitly elsewhere). Indicates a protocol mismatch, not a business error.
    """


class OdooAuthenticationError(OdooIntegrationError):
    """Login/authenticate failed — wrong database, username, password, or API
    key. Never retried automatically (rule: "do not retry authentication
    failures... blindly").
    """


class OdooAuthorizationError(OdooIntegrationError):
    """Authenticated, but the user lacks access rights for the requested model
    or operation (Odoo's own ir.model.access / record rules denied it).
    """


class OdooRemoteError(OdooIntegrationError):
    """Odoo returned an application-level error (a Python traceback/exception
    inside the JSON-RPC `error` field) that isn't better classified as
    authentication/authorization/validation/not-found.
    """


class OdooValidationError(OdooIntegrationError):
    """Odoo rejected the request due to a business validation rule (e.g. a
    required field missing, a constraint violated). Not retried blindly — the
    same input will fail again.
    """


class OdooRecordNotFoundError(OdooIntegrationError):
    """A `read`/`search_read`/`name_get` call resolved to zero records for ids
    that were expected to exist.
    """


class OdooRateLimitError(OdooIntegrationError):
    """Odoo (or a fronting proxy) signaled the client is being rate-limited.
    Safe to retry with backoff, unlike most 4xx-equivalent failures.
    """


class OdooReadOnlyViolationError(OdooIntegrationError):
    """Raised when code attempts a write-oriented Odoo method (create, write,
    unlink, copy, action_archive, action_unarchive, or any other method not on
    the client's explicit read-only allowlist) while the client is running in
    Phase 4's read-only mode. This is a programming-error guard, not a runtime
    condition the caller is expected to handle — it should never fire in
    correct code.
    """


class OdooWriteNotAllowedError(OdooIntegrationError):
    """Raised by OdooWriteClient (Phase 5) when code attempts a (model, method) pair
    outside WRITE_ALLOWED_OPERATIONS, or attempts any write while the execution
    context's mode is not APPLY. Like OdooReadOnlyViolationError, this is a
    programming-error / safety-gate guard — it should never fire when the importer is
    used as designed, since the service layer only calls allowed operations.
    """
