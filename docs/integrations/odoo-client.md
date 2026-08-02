# Odoo Client — Architecture (Phase 4)

Phase 4 deliverable. Defines the Odoo integration client built in
`backend/app/integrations/odoo/`: what it is, the protocol decision, the module
structure, and what is explicitly *not* built yet.

## 1. Scope

This phase builds a **read-only** Odoo integration boundary: connectivity/version
checks, authentication, metadata/capability discovery, catalogue field-mapping
evidence gathering, and a dry-run import planner. It does **not** import categories or
products, does not write to Odoo in any way, and does not sync data into PostgreSQL.
See [odoo-read-only-safety.md](odoo-read-only-safety.md) for how that constraint is
enforced in code, not just by convention.

## 2. Protocol decision: JSON-RPC

Odoo's standard "External API" is exposed two ways on every self-hosted edition:
XML-RPC (`/xmlrpc/2/common`, `/xmlrpc/2/object`) and JSON-RPC (`/jsonrpc`, same
`service`/`method` dispatch). Both have existed since Odoo 8 and require no additional
installed module.

**Decision: JSON-RPC.** Reasons:

- The project already depends on `httpx` (see `backend/pyproject.toml`) for other
  outbound HTTP; JSON-RPC lets the client use it directly with plain `dict` payloads,
  instead of adding `xmlrpc.client` (stdlib, but a different, more awkward calling
  convention: positional-only, no keyword args, XML marshalling errors are harder to
  classify cleanly).
- JSON-RPC error bodies are structured JSON (`{"error": {"message", "data": {...}}}`),
  which is easier to map onto the typed exception hierarchy in
  [odoo-read-only-safety.md](odoo-read-only-safety.md) than XML-RPC faults.
- Both protocols dispatch to the *same* underlying `service`/`method` pairs
  (`common.authenticate`, `object.execute_kw`, etc.), so nothing about this decision
  is Odoo-version-specific — it applies identically on Odoo 8 through the version
  actually verified in this phase.

This was evaluated, not assumed: `docs/architecture/integration-principles.md` §1
already flagged XML-RPC/JSON-RPC as the default expectation pending version
confirmation. `verify_odoo_connection --check-connection` (§
[odoo-environment-verification.md](odoo-environment-verification.md)) captures the
real server version once run against a live instance; the confirmed version (19.0)
does expose a materially different "JSON-2" API, which was evaluated live in Phase
4B (below) — the outcome is "evaluated, not adopted", not a silent swap.

`ODOO_PROTOCOL` (`backend/.env`) is currently constrained to `jsonrpc` — see
`app/integrations/odoo/config.py`'s `SUPPORTED_PROTOCOLS`. It exists as a setting (not
a hardcoded literal) so a future protocol addition doesn't require touching every
caller, but only `jsonrpc` validates today.

## 2a. JSON-2 evaluation (Phase 4B, live evidence, 2026-07-28)

Odoo 19 (confirmed server version `19.0-20260720`, self-hosted/on-premise — see
[odoo-environment-verification.md](odoo-environment-verification.md)) exposes a second,
newer external API alongside `/jsonrpc`: routes of the shape
`POST /json/2/<model>/<method>`. This was **verified empirically against the live
`terrific_dev` instance**, read-only, not assumed from documentation:

| Check | Result | Evidence |
|---|---|---|
| Route exists | **Yes** | `GET /json/2` returns Odoo's own `werkzeug.exceptions.NotFound` with the message `"Did you mean POST /json/2/<model>/<method>?"` — the server itself confirms the route pattern. |
| Auth mechanism | **API key (Bearer token) only** | `POST /json/2/res.company/search_read` with no `Authorization` header → `401 "User not authenticated, use an API Key with a Bearer Authorization header."` With `Authorization: Bearer <ODOO_PASSWORD>` → `401 "Invalid apikey"` — JSON-2 does **not** accept the database/login/password triple JSON-RPC uses; it requires a real Odoo API key. |
| Authentication works with current config | **No** | `backend/.env` has `ODOO_PASSWORD` set but no `ODOO_API_KEY` (confirmed via `Settings` — never printed). JSON-2 cannot authenticate with a password. |
| `/doc` (Odoo's built-in API docs page) | **Present but session-gated** | `GET /doc` and `/doc/` both return `303` redirecting to `/web/login?redirect=...` — the controller exists but requires an interactive web session cookie, a third, different auth mechanism this client doesn't implement (and wasn't asked to). Not pursued further — out of scope for a read-only API-client evaluation. |
| Catalogue-model/method access via JSON-2 | **Not verified** | Blocked by the authentication gap above — cannot be checked without provisioning an API key. |

**Decision: retain JSON-RPC as the only supported protocol for now.** Per the
evaluation criteria (available, supports catalogue ops, authentication works, models/
methods accessible), JSON-2 fails on "authentication works" with the credential
currently configured — not because JSON-2 is unsuitable, but because provisioning an
Odoo API key (Settings → Users → a user → Account Security → API Keys) is itself a
**write operation** inside Odoo, and this phase is explicitly read-only. Creating one
was correctly out of scope here, not attempted.

`SUPPORTED_PROTOCOLS` in `app/integrations/odoo/config.py` is unchanged
(`{"jsonrpc"}`) — no code changes were made toward JSON-2 in this phase, and none were
warranted: the instructions are to add focused tests for JSON-2 only if it's being
recommended, and it isn't (yet). JSON-RPC continues to satisfy every read-only need
this client has.

**Follow-up (not this phase):** once an `ODOO_API_KEY` is provisioned by an operator
(an ops action, not a code change), re-run this same evaluation — confirm JSON-2
authentication succeeds, then confirm `search`/`search_read`/`fields_get`-equivalent
operations work against `product.template`/`product.category`/etc. under the new
routes — before ever changing `ODOO_PROTOCOL`. Until then this remains "evaluated, not
adopted," and the existing JSON-RPC client stays as-is per the explicit instruction not
to remove it before JSON-2 is fully verified and tested.

## 3. Module structure

```
backend/app/integrations/odoo/
├── __init__.py              # public re-exports (client, config, exceptions, transport)
├── client.py                 # OdooClient — the only class allowed to call the transport
├── config.py                  # OdooConfig.from_settings() — fail-fast validation
├── transport.py               # JSON-RPC HTTP call, retries/backoff, error translation
├── authentication.py          # common.authenticate / common.version
├── exceptions.py              # stable exception hierarchy (never a raw httpx/JSON error)
├── models.py                  # internal DTOs (OdooServerVersion, ModelAvailability, ...)
├── serializers.py              # raw Odoo response -> DTO parsing
├── repositories/               # one file per Odoo model area, all read-only
│   ├── metadata.py             # server metadata, model availability, access rights
│   ├── products.py, categories.py, taxes.py, units_of_measure.py,
│   │   currencies.py, pricelists.py, stock.py
└── discovery/
    ├── capabilities.py          # orchestrates the full environment-verification checklist
    ├── fields.py                 # bounded fields_get sweep across catalogue-relevant models
    └── catalogue_mapping.py      # canonical-field -> Odoo-field evidence-based classification
```

### Deviation from `integration-principles.md`

`docs/architecture/integration-principles.md` §1 sketches a *smaller* future shape
(`client.py`, `mappers.py`, `product_adapter.py`, `order_adapter.py`, `exceptions.py`)
— that sketch describes the eventual full read+write adapter (product sync, order
export) once those phases land. Phase 4 only needs the read-only surface, but needs
*more* of it: metadata discovery, per-model repositories, and the mapping/discovery
logic that produces the field-mapping evidence report. The fuller tree above is a
superset built to satisfy this phase's explicit deliverables (repositories/,
discovery/) — not a departure from the target architecture. When product/order
adapters are built, they will sit alongside `repositories/` and reuse
`client.py`/`transport.py`/`authentication.py` unchanged; `mappers.py` (record ⇄ DTO
translation, both directions, including writes) is deferred until there is a write
path to translate for.

## 4. Dependency-injection / testability

`OdooClient` and `OdooAuthenticator` depend on `SupportsOdooCall` (a `Protocol` in
`transport.py`), not the concrete `OdooTransport` class — every unit test in
`backend/tests/unit/odoo/` injects a `FakeTransport` test double that implements the
same `.call()` signature, so the entire client/repository/discovery stack is testable
without a network call or a real Odoo instance. See
[odoo-testing.md](odoo-testing.md).

## 5. What this phase does not build

- No product/category import into Odoo (`create`/`write` are structurally blocked —
  [odoo-read-only-safety.md](odoo-read-only-safety.md)).
- No product-sync worker, no Odoo → PostgreSQL data flow.
- No order export / write-capable adapter.
- No catalogue API for the frontend; no Storefront/Admin wiring.
