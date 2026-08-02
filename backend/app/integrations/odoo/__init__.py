"""Odoo integration adapter (Phase 4: environment verification + read-only client).

Per docs/architecture/component-view.md and integration-principles.md, this is the
only package in the repository allowed to know about Odoo's API shapes,
authentication, or protocol — nothing outside app/integrations/odoo/ imports
httpx-against-Odoo directly, constructs a JSON-RPC payload, or parses a raw Odoo
response.

Phase 4 scope: read-only client, metadata/capability discovery, catalogue field-
mapping evidence gathering, dry-run import planning. No write methods are exposed —
see client.py's READONLY_ALLOWED_METHODS. Write-capable adapters (product sync writes
to PostgreSQL only; order export writes to Odoo) are future work building on this same
client/transport/authentication foundation — see docs/integrations/odoo-client.md
"What this phase does not build".
"""

from __future__ import annotations

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import (
    OdooAuthenticationError,
    OdooAuthorizationError,
    OdooConfigurationError,
    OdooConnectionError,
    OdooIntegrationError,
    OdooProtocolError,
    OdooRateLimitError,
    OdooReadOnlyViolationError,
    OdooRecordNotFoundError,
    OdooRemoteError,
    OdooTimeoutError,
    OdooValidationError,
)
from app.integrations.odoo.transport import OdooTransport

__all__ = [
    "OdooClient",
    "OdooConfig",
    "OdooTransport",
    "OdooIntegrationError",
    "OdooConfigurationError",
    "OdooAuthenticationError",
    "OdooAuthorizationError",
    "OdooConnectionError",
    "OdooTimeoutError",
    "OdooProtocolError",
    "OdooRemoteError",
    "OdooValidationError",
    "OdooRecordNotFoundError",
    "OdooRateLimitError",
    "OdooReadOnlyViolationError",
]
