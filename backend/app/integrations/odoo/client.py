"""The Odoo integration client — Phase 4 read-only surface.

Every method here maps 1:1 to a documented Odoo external-API call (`common.*` for
auth/version, `object.execute_kw` for everything else). This is the *only* class in
the repository allowed to call OdooTransport directly; repositories/ and discovery/
call this client, never the transport.

Read-only enforcement (this phase's hard constraint): `execute_readonly` only accepts
methods on READONLY_ALLOWED_METHODS. Any write-oriented method — including but not
limited to create/write/unlink/copy/action_archive/action_unarchive — raises
OdooReadOnlyViolationError before any network call is made.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.integrations.odoo.authentication import OdooAuthenticator
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import (
    OdooAuthenticationError,
    OdooAuthorizationError,
    OdooReadOnlyViolationError,
    OdooRemoteError,
    OdooValidationError,
)
from app.integrations.odoo.models import (
    AccessRights,
    OdooFieldDescriptor,
    OdooServerVersion,
    OdooSession,
    SearchReadPage,
)
from app.integrations.odoo.serializers import parse_fields_get
from app.integrations.odoo.transport import SupportsOdooCall

# Read-only methods this client will dispatch through execute_readonly(). Anything
# not in this set is rejected — an allowlist, not a blocklist, so an Odoo method this
# client doesn't yet know about is refused by default rather than accidentally
# permitted.
READONLY_ALLOWED_METHODS = frozenset(
    {
        "search",
        "search_count",
        "read",
        "search_read",
        "fields_get",
        "name_get",
        "name_search",
        "check_access_rights",
        "default_get",
        "read_group",
        "get_metadata",
    }
)

# Explicit write-method examples called out by the phase brief — kept as its own
# constant so a test can assert each one individually raises, independent of whatever
# else is or isn't in READONLY_ALLOWED_METHODS.
KNOWN_WRITE_METHODS = frozenset(
    {"create", "write", "unlink", "copy", "copy_data", "action_archive", "action_unarchive"}
)


class OdooClient:
    """Constructed with a config and a transport (dependency-injected — tests pass a
    fake transport, never a real httpx.Client). Call `.authenticate()` once before
    any other method; every other method requires an active session.
    """

    def __init__(self, config: OdooConfig, transport: SupportsOdooCall) -> None:
        self._config = config
        self._transport = transport
        self._authenticator = OdooAuthenticator(config, transport)
        self._session: OdooSession | None = None

    @property
    def session(self) -> OdooSession:
        if self._session is None:
            raise OdooAuthenticationError(
                "OdooClient method called before authenticate() succeeded"
            )
        return self._session

    def is_authenticated(self) -> bool:
        return self._session is not None

    @property
    def config(self) -> OdooConfig:
        """Read-only access to the client's configuration — safe to expose since
        OdooConfig never stores a raw credential outside its own `credential`/
        `masked_dict()` accessors.
        """
        return self._config

    # -- session -------------------------------------------------------------------

    def get_server_version(self, *, correlation_id: str | None = None) -> OdooServerVersion:
        return self._authenticator.get_server_version(correlation_id=correlation_id)

    def authenticate(self, *, correlation_id: str | None = None) -> OdooSession:
        self._session = self._authenticator.authenticate(correlation_id=correlation_id)
        return self._session

    # -- metadata / access -----------------------------------------------------------

    def check_access_rights(
        self, model: str, operation: str, *, correlation_id: str | None = None
    ) -> AccessRights:
        """`operation` is one of Odoo's own operation names: read/write/create/unlink.
        Always issued with `raise_exception=False` so a denial comes back as data
        (`allowed=False`), not as a thrown OdooAuthorizationError — callers that want
        the exception form should use `_execute` directly with default kwargs.
        """
        allowed = self.execute_readonly(
            model,
            "check_access_rights",
            [operation],
            {"raise_exception": False},
            correlation_id=correlation_id,
        )
        return AccessRights(model=model, operation=operation, allowed=bool(allowed))

    def fields_get(
        self,
        model: str,
        field_names: list[str] | None = None,
        *,
        correlation_id: str | None = None,
    ) -> dict[str, OdooFieldDescriptor]:
        """`field_names`, if given, restricts *which fields* are described — Odoo's
        `fields_get(allfields, attributes)` takes the field-name restriction as its
        first positional argument, not as an `attributes` kwarg (that kwarg instead
        restricts which *info keys* — string/type/selection/required/... — are
        returned per field, a different axis entirely; passing field names there
        silently returns every field with only the requested info keys, which is not
        what "give me just this field" means). We never restrict info keys — every
        caller needs `selection` at minimum, so the full per-field info dict is
        always requested.
        """
        args: list[Any] = [field_names] if field_names else []
        raw = self.execute_readonly(model, "fields_get", args, {}, correlation_id=correlation_id)
        return parse_fields_get(raw)

    # -- reads -----------------------------------------------------------------------

    def search(
        self,
        model: str,
        domain: list[Any],
        *,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        correlation_id: str | None = None,
    ) -> list[int]:
        kwargs: dict[str, Any] = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_readonly(
            model, "search", [domain], kwargs, correlation_id=correlation_id
        )

    def search_count(
        self, model: str, domain: list[Any], *, correlation_id: str | None = None
    ) -> int:
        return self.execute_readonly(
            model, "search_count", [domain], {}, correlation_id=correlation_id
        )

    def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
        *,
        correlation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if fields:
            kwargs["fields"] = fields
        return self.execute_readonly(model, "read", [ids], kwargs, correlation_id=correlation_id)

    def search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str] | None = None,
        *,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        correlation_id: str | None = None,
    ) -> SearchReadPage:
        effective_limit = limit if limit is not None else self._config.read_batch_size
        kwargs: dict[str, Any] = {"offset": offset, "limit": effective_limit}
        if fields:
            kwargs["fields"] = fields
        if order:
            kwargs["order"] = order
        records = self.execute_readonly(
            model, "search_read", [domain], kwargs, correlation_id=correlation_id
        )
        return SearchReadPage(records=records, offset=offset, limit=effective_limit)

    def iter_search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str] | None = None,
        *,
        order: str | None = None,
        batch_size: int | None = None,
        max_records: int,
        correlation_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Pages through up to `max_records` results, `batch_size` (default
        ODOO_READ_BATCH_SIZE) rows per request. `max_records` is a required keyword —
        deliberately no "fetch everything" convenience, per the phase constraint not
        to fetch an entire large Odoo table without a bound.
        """
        effective_batch = batch_size or self._config.read_batch_size
        fetched = 0
        offset = 0
        while fetched < max_records:
            page_limit = min(effective_batch, max_records - fetched)
            page = self.search_read(
                model,
                domain,
                fields,
                offset=offset,
                limit=page_limit,
                order=order,
                correlation_id=correlation_id,
            )
            if not page.records:
                return
            yield from page.records
            fetched += page.returned_count
            offset += page.returned_count
            if not page.has_more:
                return

    def name_get(
        self, model: str, ids: list[int], *, correlation_id: str | None = None
    ) -> list[tuple[int, str]]:
        try:
            result = self.execute_readonly(
                model, "name_get", [ids], {}, correlation_id=correlation_id
            )
            return [(int(rec_id), name) for rec_id, name in result]
        except OdooRemoteError:
            # name_get was deprecated in favor of reading display_name directly on
            # some newer Odoo versions — fall back rather than fail the caller.
            records = self.read(model, ids, ["display_name"], correlation_id=correlation_id)
            return [(int(r["id"]), r.get("display_name", "")) for r in records]

    # -- generic escape hatch, still read-only-enforced -------------------------------

    def execute_readonly(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        *,
        correlation_id: str | None = None,
    ) -> Any:
        if method in KNOWN_WRITE_METHODS or method not in READONLY_ALLOWED_METHODS:
            raise OdooReadOnlyViolationError(
                f"Refusing to call {model}.{method}: not a read-only method permitted "
                "in this phase (see app/integrations/odoo/client.py READONLY_ALLOWED_METHODS)",
                context={"model": model, "method": method},
            )
        session = self.session
        call_args = [
            session.database,
            session.uid,
            self._config.credential,
            model,
            method,
            args or [],
            kwargs or {},
        ]
        try:
            return self._transport.call(
                "object", "execute_kw", call_args, retryable=True, correlation_id=correlation_id
            )
        except OdooRemoteError as exc:
            reclassified = _classify_remote_error(exc, model, method)
            if reclassified is not None:
                raise reclassified from exc
            raise


def _classify_remote_error(exc: OdooRemoteError, model: str, method: str) -> Exception | None:
    """Best-effort reclassification of a generic OdooRemoteError into a more specific
    exception, based on substrings Odoo's own tracebacks conventionally contain.
    Returns None (leave as OdooRemoteError) when nothing matches — a safe default
    since OdooRemoteError is still a stable, typed exception callers can catch.
    """
    text = exc.message.lower()
    context = {"model": model, "method": method}
    if "accessdenied" in text or "access rights" in text or "access error" in text:
        return OdooAuthorizationError(exc.message, context=context)
    if "validationerror" in text or "constraint" in text:
        return OdooValidationError(exc.message, context=context)
    return None
