# API Standards

## 1. Versioning

- All routes are prefixed `/api/v1/...`. The version is in the URL path, not a header —
  simplest for browser `fetch` calls and easy to reason about during the migration, when
  frontend and backend land in the same PR/slice most of the time anyway.
- A breaking change to a resource's request/response shape ships as `/api/v2/<resource>`
  for that resource; unaffected resources stay on `v1`. Whole-API version bumps are not
  required for a localized change — avoids a big-bang "v2 of everything."
- `v1` is not broken during the migration described in
  [implementation-roadmap.md](implementation-roadmap.md) — routes are added
  incrementally, one vertical slice at a time, never removed/reshaped out from under a
  frontend call site still using them.
- Internal (non-browser-facing) endpoints, e.g. the Odoo status-callback webhook
  (§[integration-principles.md](integration-principles.md) §4), live under
  `/api/v1/integrations/...` — versioned the same way, but documented separately as not
  part of the public contract.

## 2. Resource/route conventions

- Nouns, plural, kebab-case where multi-word: `/api/v1/products`, `/api/v1/cart-items`,
  `/api/v1/delivery-slots`.
- Admin routes live under `/api/v1/admin/...` (e.g. `/api/v1/admin/products`,
  `/api/v1/admin/staff`) — a distinct namespace, not a query param or header flag, so
  authorization middleware can apply a blanket admin-session check at the router level
  (§[security-boundaries.md](security-boundaries.md)).
- Standard REST verbs (`GET`/`POST`/`PATCH`/`DELETE`); no verb-in-URL RPC-style endpoints
  except where an action genuinely isn't a CRUD operation on a resource (e.g.
  `POST /api/v1/orders/{id}/cancel`, `POST /api/v1/checkout/{id}/apply-promo`).
- Pagination: cursor or offset/limit (`?limit=&offset=`) on every list endpoint from day
  one — the audit already flagged client-side-only, unpaginated catalogue filtering as a
  scaling risk ([frontend-architecture.md](../current-state/frontend-architecture.md)
  §Performance concerns); the API must not repeat that.

## 3. Request/response conventions

- JSON in, JSON out. Pydantic models define every request and response shape — no
  hand-built dicts crossing the route boundary.
- Field naming: `snake_case` in the API (Python/Pydantic convention); the frontend API
  client layer (§[component-view.md](component-view.md) §5) is the one place that
  translates to/from whatever casing the existing TypeScript types use, so this is not a
  cross-cutting concern for every call site.
- Money values: integer minor units (halalas, i.e. SAR × 100) or a fixed-precision
  decimal string — never a floating-point number — to avoid the class of rounding bugs
  that's easy to introduce when porting the existing store's cart-math logic.
- Timestamps: ISO 8601, UTC, on the wire; localized/formatted for display only in the
  frontend (fixing the audit's finding that `OrderStatusTimeline`/`ProductReviews` use
  locale-blind `toLocaleDateString()` — [components.md](../current-state/components.md)).

## 4. Error-response envelope

Every non-2xx response uses one consistent shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary, safe to show or log.",
    "correlation_id": "req_9f2c1a...",
    "details": [
      { "field": "email", "issue": "not a valid email address" }
    ]
  }
}
```

- `code` is a stable, machine-checkable string (`VALIDATION_ERROR`, `NOT_FOUND`,
  `UNAUTHORIZED`, `FORBIDDEN`, `CONFLICT`, `RATE_LIMITED`, `UPSTREAM_UNAVAILABLE`,
  `INTERNAL_ERROR`) — the frontend switches on `code`, not on `message` text or HTTP
  status alone, so copy changes never break error handling.
- `correlation_id` matches the request's correlation/trace id
  (§[observability.md](observability.md)) so a user-reported error can be found in logs
  immediately.
- `details` is optional, present for validation errors, omitted otherwise.
- HTTP status codes follow standard semantics (400 validation, 401 unauthenticated, 403
  unauthorized, 404 not found, 409 conflict, 422 semantic validation, 429 rate limited,
  502/503 for confirmed upstream — e.g. Odoo — unavailability surfaced *without* ever
  blocking a normal storefront request on Odoo per rule 6; this status only applies to the
  narrow admin/internal endpoints that might synchronously check integration health).
- A single FastAPI exception-handler layer (`app/core/errors.py`) maps internal
  exceptions (including the Odoo adapter's typed exceptions,
  §[integration-principles.md](integration-principles.md)) to this envelope — individual
  route handlers do not hand-build error JSON, keeping rule 13 ("route handlers must
  remain thin") true for the failure path too.

## 5. Idempotency for unsafe operations

Any client-retryable write that must not double-apply (order creation being the
canonical case) accepts an `Idempotency-Key` header; the service layer checks it before
performing the write and returns the original result on a repeat. This is a frontend-facing
mirror of the same idempotency discipline the Odoo adapter applies internally
(§[integration-principles.md](integration-principles.md)) — protects against a real user
double-clicking "place order" or a flaky connection causing a client-side retry.

## 6. Documentation

FastAPI's generated OpenAPI schema (`/api/v1/openapi.json`, browsable at `/docs` in
non-production environments) is the source of truth for the contract — no hand-maintained
API reference to keep in sync separately.
