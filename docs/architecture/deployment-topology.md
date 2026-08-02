# Deployment Topology

Defines local, test, and production deployment shape (task 16).

## 1. Local development

Docker Compose (`docker-compose.yml` at repo root), one command to a fully working stack:

```
services:
  postgres      # postgres:16, volume-persisted, exposed for local psql/inspection
  redis         # redis:7, Celery broker + result backend + cache
  backend-api   # backend/Dockerfile, uvicorn --reload, mounts backend/app for live reload
  celery-worker # same image as backend-api, `celery -A app.workers worker`
  celery-beat   # same image, `celery -A app.workers beat`
```

- The existing frontend runs as it does today, outside Compose (`bun run dev` /
  `npm run dev`), pointed at the local FastAPI via an env var (`VITE_API_BASE_URL` or
  equivalent) — not containerized, since that's not how it's developed today and rule 20
  doesn't ask for a dev-workflow change.
- Odoo itself is **not** part of local Compose by default — developers point the backend
  at a shared Odoo sandbox/staging instance (credentials via untracked `.env.local`), since
  standing up a full local Odoo is heavy and the adapter's contract tests
  (§[testing-strategy.md](testing-strategy.md)) don't require it. A local Odoo profile can
  be added later if that friction proves real.
- `backend/.env.example` documents every required variable with placeholder/non-secret
  values; real values live in an untracked `.env` (already the pattern the audit expects —
  see [target-architecture.md](target-architecture.md) C9).

## 2. Test / staging environment

- Same container images as production (built once, promoted, not rebuilt per
  environment) — backend API, Celery worker, Celery beat.
- Dedicated Postgres and Redis instances (managed or containerized), isolated from
  production data.
- Points at an Odoo **staging/sandbox** instance, not production Odoo — sync/export tests
  against staging are exactly what makes the Odoo-adapter risk in
  [testing-strategy.md](testing-strategy.md) §3 tractable.
- Seeded with realistic but non-production fixture data (rule 23 — no hardcoded
  production data; seed data is clearly fixture data, loaded via a script/fixture file, not
  baked into application code).
- CI deploys here automatically on merge to the main integration branch (exact trigger
  policy TBD by the team); this is where the "actual command verification" smoke tests
  (§[testing-strategy.md](testing-strategy.md) §3) run against a live, deployed stack, not
  just locally.

## 3. Production

- **Frontend**: unchanged from today — the existing Nitro/Cloudflare Workers deployment
  path (or whatever the team runs it on today via Lovable) continues to serve the
  storefront/admin UI; it now points its API base URL at the production FastAPI instead of
  `localStorage`.
- **Backend API**: containerized FastAPI, multiple replicas behind a load balancer/reverse
  proxy, horizontally scalable independent of workers (API load and sync/export load don't
  necessarily correlate).
- **Workers**: Celery workers as a separately scaled deployment/pool from the API — sync
  and order-export volume can spike independently of storefront traffic.
- **Scheduler**: Celery Beat runs as a **single active instance** (a second replica would
  double-fire every scheduled task) — either one dedicated small process, or a
  leader-election pattern if the deployment platform makes single-instance guarantees
  awkward. This is a real operational constraint, not a nice-to-have.
- **PostgreSQL**: managed instance (e.g., a managed Postgres service) with automated
  backups and point-in-time recovery — this is now the storefront's operational database
  (rule 4); losing it is losing carts/orders/sessions, not just a cache.
- **Redis**: managed instance, persistence not critical (Celery broker state and cache are
  acceptable to lose and rebuild, unlike Postgres).
- **Odoo**: production Odoo instance, reached over a private network path (VPN/private
  link/IP allowlist) rather than the open internet where possible — exact network topology
  depends on where Odoo is hosted (self-hosted vs. Odoo.sh vs. a partner-hosted instance),
  an open question (see [implementation-roadmap.md](implementation-roadmap.md)).
- **Secrets**: environment variables sourced from the platform's secrets manager (exact
  provider TBD alongside the hosting decision) — DB credentials, Redis URL, JWT signing
  key, Odoo API credentials, payment-provider keys. Never committed (rule 22), never
  logged (§[observability.md](observability.md) §2).
- **TLS**: terminated at the load balancer/reverse proxy in front of FastAPI; the existing
  frontend's own hosting already terminates TLS for the UI.

## 4. What's explicitly deferred

Per [target-architecture.md](target-architecture.md) §4, this topology does not include
Kubernetes, a service mesh, or multi-region active-active deployment — a handful of
horizontally-scaled containers behind a load balancer, plus managed Postgres/Redis, is
sufficient for the described scale and matches the "modular monolith, minimal
infrastructure" stance. Revisit only if a demonstrated production requirement (traffic,
availability SLA, compliance) justifies it — see
[architecture-decision-records.md](architecture-decision-records.md).
