"""The Odoo write-capable client — Phase 5's controlled write boundary.

Deliberately a separate class from OdooClient (app/integrations/odoo/client.py), not a
subclass or a flag on it: OdooClient's READONLY_ALLOWED_METHODS gate is untouched, stays
the default for every other caller (verify_odoo_connection, plan_odoo_catalogue_import,
every repository under app/integrations/odoo/repositories/), and nothing in this module
weakens it. OdooWriteClient is its own allowlisted, audited, context-gated surface that
only the Phase 5 catalogue importer (app/services/catalogue/odoo_import_service.py)
constructs.

Three independent gates must all pass before a single Odoo write happens:
1. `context.mode == "APPLY"` — constructing/using this client during --validate,
   --plan, or --dry-run is fine (the service does so to reuse the same code path), but
   any actual call raises OdooWriteNotAllowedError unless the mode is APPLY.
2. `(model, method)` must be in WRITE_ALLOWED_OPERATIONS — a closed allowlist, not a
   blocklist. unlink/copy/action_archive/action_unarchive/module install/stock
   writes/tax or UoM or pricelist creation/company or access-right changes are refused
   simply by never appearing here — there is no bypass argument.
3. Every call requires a WriteAudit — external_key, planned_operation, and (for
   updates) a before_state snapshot are mandatory, not optional kwargs, so a write can
   never be issued without the bookkeeping the service layer needs to persist an
   odoo_catalogue_import_items audit row.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.integrations.odoo.authentication import OdooAuthenticator
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooAuthenticationError, OdooWriteNotAllowedError
from app.integrations.odoo.models import OdooSession
from app.integrations.odoo.transport import SupportsOdooCall

logger = logging.getLogger("app.integrations.odoo.write_client")

# Closed allowlist of (model, method) pairs this client will ever call. Matches
# CLAUDE.md Phase 5 brief section 2 exactly. Anything not listed here — unlink, copy,
# action_archive, action_unarchive, stock.*, account.tax.create, uom.uom.create,
# product.pricelist.create, res.company writes, ir.module.module.*, res.users/
# ir.model.access writes — is refused unconditionally.
WRITE_ALLOWED_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("product.category", "create"),
        ("product.category", "write"),
        ("product.template", "create"),
        ("product.template", "write"),
        ("product.product", "write"),
        ("product.image", "create"),
        ("product.image", "write"),
        ("ir.model.data", "create"),
        # Variant-attribute modelling (docs/integrations/odoo-catalogue-variant-model.md):
        # attributes/values are shared master data (create only — matched by name before
        # ever created, never re-created; see plan_attributes()). template.attribute.line
        # is the actual mechanism that makes Odoo auto-generate/adjust product.product per
        # combination; .write lets an existing axis gain a new value without deleting and
        # recreating the line (which would risk Odoo deleting a variant that already has
        # stock/sale history). template.attribute.value gets write only — Odoo creates
        # these itself as a side effect of the line create/write, never called directly.
        ("product.attribute", "create"),
        ("product.attribute.value", "create"),
        ("product.template.attribute.line", "create"),
        ("product.template.attribute.line", "write"),
        ("product.template.attribute.value", "write"),
    }
)

# Methods this client will never expose, even indirectly — kept as its own constant
# purely so a test can assert each one individually raises, independent of whatever
# else is or isn't allowlisted (mirrors client.py's KNOWN_WRITE_METHODS pattern).
EXPLICITLY_FORBIDDEN_METHODS = frozenset(
    {"unlink", "copy", "copy_data", "action_archive", "action_unarchive"}
)

VALID_IMPORT_MODES = ("VALIDATE", "PLAN", "DRY_RUN", "APPLY", "ROLLBACK_PLAN")


@dataclass(frozen=True)
class ImportExecutionContext:
    """Identifies the import run a write is happening under. Constructing an
    OdooWriteClient without one is a type error, not a runtime check — every write is
    traceable to exactly one run_id/correlation_id/initiated_by triple.
    """

    run_id: uuid.UUID
    correlation_id: str
    initiated_by: str
    mode: str

    def __post_init__(self) -> None:
        if self.mode not in VALID_IMPORT_MODES:
            raise ValueError(
                f"Invalid import mode {self.mode!r} — must be one of {VALID_IMPORT_MODES}"
            )

    @property
    def writes_permitted(self) -> bool:
        return self.mode == "APPLY"


@dataclass(frozen=True)
class WriteAudit:
    """Mandatory bookkeeping attached to every create()/write() call. The service
    layer turns this (plus the resulting Odoo id) into an odoo_catalogue_import_items
    row — this module only logs it structurally, it never touches PostgreSQL.
    """

    entity_type: (
        str  # CATEGORY | PRODUCT_TEMPLATE | PRODUCT_VARIANT | PRODUCT_IMAGE | EXTERNAL_XML_ID
        # | PRODUCT_ATTRIBUTE | PRODUCT_ATTRIBUTE_VALUE
    )
    canonical_external_key: str
    planned_operation: str  # CREATE | UPDATE
    before_state: dict[str, Any] | None = None


class OdooWriteClient:
    """Constructed with a config, transport, and ImportExecutionContext — mirrors
    OdooClient's dependency-injected shape so tests can pass a fake transport, but
    intentionally does not share OdooClient's READONLY_ALLOWED_METHODS machinery: this
    is additive, not a loosened version of the read-only client.
    """

    def __init__(
        self, config: OdooConfig, transport: SupportsOdooCall, context: ImportExecutionContext
    ) -> None:
        self._config = config
        self._transport = transport
        self._context = context
        self._authenticator = OdooAuthenticator(config, transport)
        self._session: OdooSession | None = None

    @property
    def context(self) -> ImportExecutionContext:
        return self._context

    @property
    def session(self) -> OdooSession:
        if self._session is None:
            raise OdooAuthenticationError(
                "OdooWriteClient method called before authenticate() succeeded"
            )
        return self._session

    def authenticate(self) -> OdooSession:
        self._session = self._authenticator.authenticate(
            correlation_id=self._context.correlation_id
        )
        return self._session

    def create(self, model: str, values: dict[str, Any], *, audit: WriteAudit) -> int:
        """Returns the new record's Odoo id."""
        result = self._execute_write(model, "create", [values], audit=audit)
        return int(result)

    def write(
        self, model: str, ids: list[int], values: dict[str, Any], *, audit: WriteAudit
    ) -> bool:
        result = self._execute_write(model, "write", [ids, values], audit=audit)
        return bool(result)

    # -- the one choke point every write goes through --------------------------------

    def _execute_write(self, model: str, method: str, args: list[Any], *, audit: WriteAudit) -> Any:
        self._enforce_gates(model, method, audit)

        session = self.session
        call_args = [
            session.database,
            session.uid,
            self._config.credential,
            model,
            method,
            args,
            {},
        ]

        log_context = {
            "correlation_id": self._context.correlation_id,
            "import_run_id": str(self._context.run_id),
            "initiated_by": self._context.initiated_by,
            "model": model,
            "method": method,
            "entity_type": audit.entity_type,
            "canonical_external_key": audit.canonical_external_key,
            "planned_operation": audit.planned_operation,
        }
        logger.info("odoo_write_attempt", extra=log_context)
        try:
            result = self._transport.call(
                "object",
                "execute_kw",
                call_args,
                retryable=False,  # writes are never blindly retried — a failed create
                # could have partially succeeded server-side; retrying risks a
                # duplicate. The service layer decides recovery (recover-by-XML-ID/
                # SKU), never a transport-level automatic retry.
                correlation_id=self._context.correlation_id,
            )
        except Exception:
            logger.exception("odoo_write_failed", extra=log_context)
            raise
        logger.info("odoo_write_succeeded", extra={**log_context, "result": result})
        return result

    def _enforce_gates(self, model: str, method: str, audit: WriteAudit) -> None:
        if (
            method in EXPLICITLY_FORBIDDEN_METHODS
            or (model, method) not in WRITE_ALLOWED_OPERATIONS
        ):
            raise OdooWriteNotAllowedError(
                f"Refusing to call {model}.{method}: not on WRITE_ALLOWED_OPERATIONS "
                "(see app/integrations/odoo/write_client.py)",
                context={"model": model, "method": method},
            )
        if not self._context.writes_permitted:
            raise OdooWriteNotAllowedError(
                f"Refusing to call {model}.{method}: import execution context mode is "
                f"{self._context.mode!r}, not APPLY — no Odoo write is permitted outside "
                "a confirmed --apply run",
                context={"model": model, "method": method, "mode": self._context.mode},
            )
        if audit.planned_operation == "UPDATE" and audit.before_state is None:
            raise OdooWriteNotAllowedError(
                f"Refusing to call {model}.{method}: planned_operation is UPDATE but no "
                "before_state snapshot was supplied — updates must be recoverable",
                context={"model": model, "method": method},
            )
