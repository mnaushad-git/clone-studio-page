# Odoo Authentication

## Mechanism

`app/integrations/odoo/authentication.py`'s `OdooAuthenticator` wraps two JSON-RPC
calls on Odoo's `common` service:

- `common.version` — no credentials required; used by
  `OdooClient.get_server_version()` to confirm reachability before attempting login.
- `common.authenticate(database, username, credential, {})` — returns an integer
  `uid` on success, or a falsy value / a remote error on failure. Odoo's external API
  accepts an API key anywhere it accepts a password, so password and API-key auth
  share this one call — `OdooConfig.credential` resolves to whichever one is
  configured (never both — `OdooConfig.from_settings()` rejects that combination).

`OdooClient.authenticate()` calls this once and caches the resulting `OdooSession`
(`uid`, `database`, `username`) for the lifetime of the client. Every subsequent
`object.execute_kw` call reuses that session; there is no per-call re-authentication.

## Configuration

One of `ODOO_PASSWORD` or `ODOO_API_KEY` must be set (not both, not neither) —
enforced by `OdooConfig.from_settings()` at construction time, before any network
call. See [environment-variables.md](../backend/environment-variables.md).

## Never logged

- `Settings.masked_dict()` and `OdooConfig.masked_dict()` both redact `password` and
  `api_key`; `SECRET_FIELD_NAMES` in `app/core/config.py` includes both, so the
  existing `SecretRedactionFilter` (`app/core/logging.py`) also scrubs either value if
  it ever appears verbatim in a log message from anywhere else in the app.
- `OdooAuthenticator` only ever logs the resulting `uid` (an integer, not a secret)
  and the database/username — never the password/API key, never a raw request/response
  body.
- `OdooIntegrationError.safe_context()` (`exceptions.py`) drops `password`, `api_key`,
  `session_id`, `auth_payload`, and `cookie` keys before a caller attaches exception
  context to a log record — a second line of defense independent of what any
  individual call site remembers to omit.
- The JSON-RPC error envelope from a failed `authenticate` call is never echoed
  verbatim into `OdooAuthenticationError`'s message with the credential embedded —
  Odoo's own `common.authenticate` error messages don't echo the password back, and
  the wrapping exception only includes `database`/`username` in its context.

## Retry policy

Authentication is **never retried automatically** (`OdooAuthenticator.authenticate()`
calls the transport with `retryable=False`). A wrong password/API key/database fails
identically on every attempt; retrying only delays surfacing a real configuration
problem and risks tripping any login-rate-limiting the Odoo instance enforces.
`get_server_version()` (no credentials involved) *is* retryable — a transient network
blip there is safe to retry.

## Verifying authentication

```
python -m app.scripts.verify_odoo_connection --check-connection --check-authentication
```

See [odoo-environment-verification.md](odoo-environment-verification.md) for the full
command and report shape.
