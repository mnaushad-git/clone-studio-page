# Testing Strategy

Defines how rule 24 ("every implementation phase must include tests and actual command
verification") is satisfied concretely, and the overall test approach (task 15). The
current codebase has **zero automated tests** anywhere
([gap-analysis.md](../current-state/gap-analysis.md) §5) — this is a genuinely new
discipline for the project, not a tightening of an existing one.

## 1. Backend (pytest)

| Layer | What's tested | How |
|---|---|---|
| **Unit** | Service-layer business logic (cart math, promo application, order-status transition rules, RBAC decisions) in isolation. | Pure pytest, repositories mocked/faked — fast, no DB or network. |
| **Repository/integration** | Repository classes against a real PostgreSQL instance (schema + query correctness, constraints, transaction behaviour — including the outbox-in-one-transaction guarantee, rule 18). | pytest + a real Postgres (docker-compose test profile or ephemeral container per run), Alembic migrations applied before the suite runs — not SQLite, since constraint/JSON/behaviour parity with production matters here. |
| **API** | Route handlers, request/response contracts, auth boundaries (a customer token cannot hit an admin route and vice versa, per [security-boundaries.md](security-boundaries.md)), error-envelope shape. | FastAPI `TestClient`/`httpx.AsyncClient` against the app with a real test DB. |
| **Odoo adapter (contract)** | Adapter's request construction and response mapping, without depending on a live Odoo instance for every CI run. | Recorded fixtures (VCR-style cassette or hand-built fixture payloads) for the common paths; a smaller, explicitly-marked suite that runs against a real Odoo sandbox/staging instance (manually or in a scheduled CI job, not on every commit) to catch real drift. |
| **Worker tasks** | Idempotency (running a task twice produces the same state), retry behaviour, checkpoint advancement. | pytest against Celery tasks run in eager/synchronous mode, real test DB. |
| **Migrations** | Every Alembic migration both upgrades and downgrades cleanly against a fresh test DB. | A dedicated migration test run in CI, not just "it worked when I wrote it." |

Coverage is not chased as a number; the bar is that every service method with a business
rule (tax calc, promo eligibility, RBAC check, sync idempotency, outbox transaction) has a
test that would fail if the rule were silently broken — matching the audit's own framing
of *why* tests matter here (§5: "every one of the fake/simulated behaviours documented
here was found by manual reading, not caught by a test suite").

## 2. Frontend

No test framework exists today. As each vertical slice replaces a `store.ts`/
`admin-store.ts` domain with real API calls (§[component-view.md](component-view.md) §5),
that slice introduces:

- **Component/unit tests** (Vitest + React Testing Library — natural fit for the existing
  Vite-based TanStack Start setup) for the replaced logic (e.g., cart total calculation
  now driven by an API response instead of local math).
- **A small number of end-to-end smoke tests** (Playwright) covering the golden paths that
  matter most for regressions: browse → add to cart → checkout → order confirmation;
  admin login → edit a product → see it reflected. Not a full E2E suite from day one —
  enough to catch a broken golden path before it ships.

Frontend testing is scoped *to what each slice touches*, not introduced as a big-bang
retrofit across all ~40 existing routes — most of the UI (static marketing pages, the
component library) has no behaviour change and doesn't need new tests just because a
backend now exists elsewhere.

## 3. "Actual command verification" (rule 24)

Every implementation phase's completion is demonstrated with real, runnable output, not a
description of intended behaviour:

```
cd backend
uv run pytest                       # or poetry/pip-tools equivalent — full backend suite
uv run alembic upgrade head          # migrations apply cleanly
uv run ruff check . && uv run mypy .  # lint/type-check gates
```

```
bun run lint                         # existing frontend lint, unchanged
bun run build                        # existing frontend build, unchanged — must still pass
bun test                             # new frontend unit tests, once introduced
```

Plus, for slices touching the Odoo flows: a manual or scripted run against a real Odoo
sandbox showing the sync/export/reconciliation actually round-tripping data — a mocked
test passing is necessary but not sufficient proof for those slices, given how much of
this architecture's risk is concentrated in "does the real Odoo API behave the way the
adapter assumes."

## 4. CI

CI (exact provider TBD — GitHub Actions is the default assumption given a GitHub-hosted
repo) runs on every PR: backend lint + type-check + unit/integration/migration tests
against a real Postgres service container, frontend lint + build (+ unit tests once they
exist). Nothing here exists today (no CI config found in the audit); it is introduced
alongside the first backend slice, not deferred (see
[implementation-roadmap.md](implementation-roadmap.md) step 1).
