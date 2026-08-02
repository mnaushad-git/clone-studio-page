# Local Development — Backend + Admin Portal

Docker is not installed on this machine, so **Option B (native Windows)** is the
primary path below. Docker Compose (Option A) is kept as the documented alternative
for other environments. No credentials are stored in this document — copy
`backend/.env.example` to `backend/.env` and fill in your own local values.

## Prerequisites

- Python 3.12
- A reachable PostgreSQL 16 instance
- Node.js (for the frontend — `npm run dev` / `bun run dev` at the repo root)
- Optional: a Redis-compatible server (Celery broker/result backend, login-throttle
  cache). The app runs without it — `/api/v1/admin/system/status` and the Admin
  Portal's operational banner report `redis: "down"` and retry actions queue but
  don't dispatch until it's back (task brief §9) — but Odoo sync/notification
  background processing needs it to actually run automatically.

## Option B — Run everything natively (no Docker)

### 1. PostgreSQL

Use any local PostgreSQL 16 instance (a native Windows install, an existing service,
etc.). Create the app database and a separate one for the test suite:

```powershell
psql -U postgres -c "CREATE DATABASE terrific_bites;"
psql -U postgres -c "CREATE DATABASE terrific_bites_test;"
```

Set `DATABASE_URL` in `backend/.env` to point at `terrific_bites`
(`postgresql+psycopg://<user>:<password>@127.0.0.1:5432/terrific_bites`).

### 2. Redis (optional but recommended)

Any Redis-compatible server reachable at `REDIS_URL` works — e.g.
[Memurai](https://www.memurai.com/) (native Windows, Redis-protocol-compatible) or
Redis running inside WSL2. Point `REDIS_URL`/`CELERY_BROKER_URL`/
`CELERY_RESULT_BACKEND` in `backend/.env` at it. If you skip this, everything except
background sync/notification dispatch and the Redis-backed login throttle still
works — the Admin Portal will show the operational banner instead of silently
pretending those systems are up.

### 3. Backend API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

Copy-Item .env.example .env    # then edit DATABASE_URL/REDIS_URL/ADMIN_JWT_SECRET etc.

alembic upgrade head           # requires DATABASE_URL reachable

uvicorn app.main:app --reload --port 8000
```

Smoke-test:

```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/version
curl http://localhost:8000/api/v1/readiness   # 200 if Postgres+Redis reachable, else 503
```

### 4. Bootstrap an admin user

No default/hardcoded admin credentials exist — create one explicitly:

```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:ADMIN_BOOTSTRAP_PASSWORD = "choose-a-strong-local-password"
python -m app.scripts.create_admin_user --email owner@terrificbites.sa --full-name "Store Owner" --role SUPER_ADMIN
Remove-Item Env:\ADMIN_BOOTSTRAP_PASSWORD
```

Omit `ADMIN_BOOTSTRAP_PASSWORD` to be prompted securely instead (no terminal echo).
Roles: `SUPER_ADMIN`, `OPERATIONS_ADMIN`, `CATALOGUE_ADMIN`, `SUPPORT_ADMIN`.

### 5. Celery worker + Beat (optional — only needed for automatic background sync)

In separate terminals, with the same venv activated:

```powershell
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
celery -A app.workers.celery_app beat --loglevel=info
```

(`--pool=solo` avoids the multiprocessing issues Celery's default prefork pool has on
Windows.) Without a worker/Beat running, paid orders and notifications stay queued in
the outbox (`order_outbox_events`, status `pending`) until you either start Beat or
run the manual drivers:

```powershell
python -m app.scripts.process_order_outbox
python -m app.scripts.process_order_notifications
```

### 6. Frontend

From the **repository root** (not `backend/`):

```powershell
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in the root `.env`/`.env.local` if the backend isn't at
`http://localhost:8000`. The Admin Portal is at `/admin` (redirects to `/admin/login`
if not authenticated); the Storefront is at `/`.

## Option A — Docker Compose

From the **repository root** (`docker-compose.yml` lives there, not under `backend/`):

```sh
docker compose up --build
```

Starts `postgres`, `redis`, `backend-api` (port `${API_PORT:-8000}`),
`celery-worker`, `celery-beat`. Apply migrations and bootstrap an admin inside the
running container:

```sh
docker compose exec backend-api alembic upgrade head
docker compose exec -e ADMIN_BOOTSTRAP_PASSWORD=your-local-password backend-api \
  python -m app.scripts.create_admin_user --email owner@terrificbites.sa --full-name "Store Owner" --role SUPER_ADMIN
```

Tear down (keeps the Postgres volume): `docker compose down`.

The frontend still runs outside Docker (`npm run dev` at the repo root) — it is not
part of `docker-compose.yml`.

## Running quality gates

Backend, from `backend/` (venv activated):

```powershell
ruff format --check .
ruff check .
mypy app
mypy scripts
pytest -q
alembic upgrade head   # requires a reachable PostgreSQL
```

Frontend, from the repo root:

```powershell
node_modules\.bin\tsc --noEmit
npm run lint
npm run test
npm run build
```

## Manual verification checklist (Admin Portal MVP)

1. Bootstrap an admin user (§4 above), start the backend and frontend.
2. Open `/admin/login`, sign in.
3. Confirm the dashboard shows real counts (orders today, revenue, alerts) — not
   placeholder data.
4. Open a real order (place one from the Storefront first if none exist), change its
   status, and confirm the change appears in `order_status_events` and
   `/admin/audit`.
5. Manually flip an outbox event to `failed` (or wait for a real failure) and use the
   retry button — confirm the row returns to `pending` and, if a worker is running,
   eventually completes.
6. Create a promo code in `/admin/promotions`, apply it at Storefront checkout,
   confirm the discount and `promo_codes.usage_count`.
7. Edit the delivery fee in `/admin/delivery` and confirm the Storefront's checkout
   total reflects it on the next order (no redeploy needed).
8. Toggle a product's Featured/New flag in `/admin/products` and confirm the
   Storefront reflects it.
9. Review `/admin/audit` for the resulting entries and `/admin/system` for
   provider/worker status.
