# Security Boundaries

Defines authentication/authorization boundaries for customers and administrators (task
13), replacing the current no-op auth described in
[gap-analysis.md](../current-state/gap-analysis.md) §1.

## 1. Guiding constraint

Both auth boundaries are enforced **server-side, in FastAPI**, never trusted from
client-supplied state. This directly closes the audit's top findings: today, admin access
is gated by reading `localStorage` in the browser with no server round-trip at all
(§1.2–1.5 of the gap analysis). Under the target architecture, the browser holds a token;
FastAPI is the only party that decides what that token is allowed to do.

## 2. Customer authentication

- **Identity**: email or phone, matching the existing `login.tsx`/`signup.tsx` UI shape
  (rule 20 — UI unchanged). Password auth (hashed with a strong KDF — argon2id or bcrypt,
  never stored/compared in plaintext, unlike... nothing today, since today's "auth"
  doesn't check a password at all) plus the existing phone-OTP UI path, backed by a real
  OTP provider once selected (open question, [implementation-roadmap.md](implementation-roadmap.md)).
- **Session**: FastAPI issues a short-lived access token + longer-lived refresh token on
  successful login (JWT or opaque server-side session token — see
  [ADR-009](architecture-decision-records.md#adr-009)). Token audience/claims are scoped
  to `customer` — cannot be replayed against an admin endpoint.
  - Web transport: httpOnly, `Secure`, `SameSite=Lax` cookie, since the frontend is
    server-rendered (TanStack Start SSR) and same-origin — avoids exposing the token to
    JS entirely and sidesteps XSS token theft.
- **Guest checkout**: preserved as a first-class path (existing `CartDrawer` already
  distinguishes guest vs. signed-in — [components.md](../current-state/components.md)) —
  a guest gets an anonymous cart/checkout-session id, no customer auth required, consistent
  with rule 20. Whether guest orders later prompt account creation is a product decision,
  not an architectural one.
- **Authorization**: a customer can only read/write their own cart, orders, addresses,
  reviews, loyalty ledger — enforced by scoping every customer-facing repository query to
  `customer_id` derived from the verified token, never from a client-supplied id in the
  request body.

## 3. Administrator authentication

- **Identity**: `admin_staff` table (replacing today's client-editable `staff` array in
  `admin-store.ts`), email + password, hashed the same way as customer passwords.
- **Session**: same token mechanism as customers, but a **separate token
  audience/claim** (`admin`) issued from a distinct `/api/v1/admin/auth/login` endpoint —
  an admin token and a customer token are never interchangeable, and a customer who is
  also staff needs two separate sessions/logins, not one token with two roles bolted on.
  This directly prevents the class of bug where a shared session accidentally grants
  storefront access to admin capability or vice versa.
- **RBAC**: roles (`owner`, `admin`, `manager`, `support`, `kitchen` — the five roles the
  existing UI already models) map to a small, explicit permission matrix enforced by a
  FastAPI dependency on every admin route (e.g. `require_role("owner", "admin")`), not by
  the frontend hiding a button. This is the direct fix for the audit's highest-severity
  finding: **self-service privilege escalation**, where any signed-in role can currently
  edit its own `role` field to `"owner"` client-side
  ([gap-analysis.md](../current-state/gap-analysis.md) §1.5). Under the target design, a
  staff member can never change their own role — that mutation requires `owner`/`admin`
  and targets a *different* staff record, enforced in `admin_identity.service`, not the UI.
- **No hardcoded credentials, anywhere** — closes §1.2 (hardcoded `"admin123"` displayed
  in a "Demo" hint on the login page) permanently; seed/demo accounts, if needed for a
  test environment, are environment-specific fixtures (rule 23), never a literal in
  application code.
- **SSR-safe guard**: today's `admin.tsx` `beforeLoad` check is a no-op during SSR
  (`if (typeof window === "undefined") return`) — the target design's session check must
  run identically server-side and client-side, since the token lives in a cookie sent on
  every request, not read out of `localStorage` after hydration.

## 4. Transport and secrets

- HTTPS everywhere, including local dev where practical (self-signed acceptable locally).
- Token signing keys, DB credentials, Odoo credentials, payment-provider keys: environment
  variables in every environment, sourced from a secrets manager in test/production, never
  committed (rule 22) — see [deployment-topology.md](deployment-topology.md).
- Payment data: the storefront never sends raw card data to FastAPI at all — the payment
  provider's client-side tokenization (e.g., hosted fields/Elements-style) replaces
  today's `payment.tsx` raw-field form, so FastAPI only ever handles an opaque payment
  token/reference, keeping PCI scope minimal. This is a checkout **data-flow** change even
  though the UI's visual shape can stay the same (rule 20 governs layout/behaviour, not
  the wire format underneath a card input).

## 5. Rate limiting and abuse controls

Login (customer and admin), OTP request, and password-reset endpoints are rate-limited
(Redis-backed) per identity and per IP — today's OTP flow accepts any 4 digits with no
limit at all, so this is a genuinely new control, not a tightening of an existing one.

## 6. What does not change

The Odoo integration adapter, background workers, and PostgreSQL are never reachable by
either a customer or an admin session token directly — both auth boundaries exist entirely
at the FastAPI layer described above (rules 1–3, [target-architecture.md](target-architecture.md)).
