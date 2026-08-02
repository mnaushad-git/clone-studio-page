# Odoo Read-Only Safety (Phase 4)

Phase 4 is read-only by explicit instruction: no category/product import, no
create/update/archive/delete of any Odoo record. This document describes how that
constraint is enforced in code, not left to reviewer discipline.

## Enforcement: an allowlist, not a blocklist

`app/integrations/odoo/client.py`'s `OdooClient.execute_readonly()` is the **only**
path by which anything in this codebase can reach `object.execute_kw`. It checks the
requested Odoo method against `READONLY_ALLOWED_METHODS`:

```python
READONLY_ALLOWED_METHODS = frozenset({
    "search", "search_count", "read", "search_read", "fields_get",
    "name_get", "name_search", "check_access_rights", "default_get",
    "read_group", "get_metadata",
})
```

Any method **not** in that set — including every write-oriented method the phase
brief names explicitly (`create`, `write`, `unlink`, `copy`, `action_archive`,
`action_unarchive`, tracked separately as `KNOWN_WRITE_METHODS` so a test can assert
each one individually) — raises `OdooReadOnlyViolationError` **before any network
call is made**. This is an allowlist deliberately, not a blocklist: an Odoo method
this client doesn't yet know about is refused by default, not accidentally permitted.

Every one of `OdooClient`'s convenience methods (`search`, `read`, `search_read`,
`fields_get`, `name_get`, `check_access_rights`) is implemented in terms of
`execute_readonly()` with a hardcoded method name — there is no way to pass an
arbitrary method string into them, so the only way to reach a forbidden method is
through `execute_readonly()` itself, where the check lives.

Test coverage: `backend/tests/unit/odoo/test_client.py::test_execute_readonly_rejects_every_known_write_method`
is parametrized over every entry in `KNOWN_WRITE_METHODS` and additionally asserts the
underlying fake transport's write-call counter stays at zero — proving the rejection
happens before any call reaches the transport, not just that an exception is raised
after the fact.

## Where this applies

- `app/integrations/odoo/repositories/*.py` — every repository method calls
  `OdooClient.search`/`search_read`/`search_count`, never `execute_readonly` with an
  arbitrary method.
- `app/integrations/odoo/discovery/*.py` — capability/field discovery is entirely
  `search_count`/`check_access_rights`/`fields_get`/`search_read`.
- `app/scripts/verify_odoo_connection.py` and `app/scripts/plan_odoo_catalogue_import.py`
  — both scripts only ever go through `OdooClient`; `plan_odoo_catalogue_import.py`'s
  conflict/external-key lookups are `search_read` calls, never a write, even when they
  determine an item's proposed action is `CREATE` (the plan is *proposed*, never
  executed).

## What is deliberately out of scope for this guard

This mechanism protects **Odoo**, not PostgreSQL — writing to the catalogue database
via `app/repositories/catalogue/*.py` (a completely different, pre-existing repository
layer from Phase 3) is unaffected and unrelated. Nothing in this phase touches those
tables.
