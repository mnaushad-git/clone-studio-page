# Local Docker stack

Runs all of Terrific Bites on one Windows machine, isolated from myMakan, Maskan and the
native PostgreSQL, Memurai and Odoo installs.

## Prerequisites

Docker Desktop on the WSL2 backend, with about 6 GB of memory given to WSL and at least
15 GB free for images and volumes. If drive C: is short of space, move Docker's disk image
to D: in Docker Desktop under Settings > Resources > Advanced.

## Start

```powershell
powershell -ExecutionPolicy Bypass -File deploy\local\Start-Stack.ps1
```

The first run creates `deploy/local/.env.local` (git-ignored) with new random secrets, builds
the images, migrates and seeds PostgreSQL, installs Odoo modules, creates the integration
user, and waits until every service is healthy.

| Option | Effect |
|---|---|
| `-Integration` | Real sale orders go to the local Odoo container. Payments and notifications stay stubbed |
| `-Action status` | Lists services and their health |
| `-Action down` | Stops the stack and keeps the data |

## Services

| Service | Published address | Purpose |
|---|---|---|
| `terrific-caddy` | `http://localhost:18080`, `http://localhost:18069` | The only published ports, loopback only |
| `terrific-frontend` | Through Caddy | Storefront and Admin Portal |
| `terrific-api` | `http://localhost:18080/api/` | FastAPI |
| `terrific-worker` | None | Celery worker |
| `terrific-beat` | None | Celery scheduler, which drives the outbox poll |
| `terrific-odoo` | `http://localhost:18069` | Odoo 19, with its own database and filestore |
| `terrific-postgres` | None | `terrific_bites` and `terrific_odoo`, each with its own role |
| `terrific-redis` | None | Broker, cache and rate limits |

## Demo and integration modes

| | Demo (default) | Integration (`-Integration`) |
|---|---|---|
| `DEPLOYMENT_STAGE` | `demo` | `local_integration` |
| Orders | Marked `is_demo`, never reach Odoo, shown as `simulated` | Real `sale.order` in `terrific-odoo` |
| Payments | Stub | Stub |

Odoo credentials reach only `terrific-worker` (order sync user) and the one-shot
`terrific-catalogue-import` (product-creating user). The API and Beat refuse to start if they
are given one.

`local_integration` refuses to start if `APP_ENV` is `production`, if the Odoo host isn't local,
or if any provider other than the Odoo push is real. Every Odoo write also has to match
`ODOO_WRITE_APPROVED_TARGET` exactly.

## Catalogue import

```powershell
$c = "docker compose --env-file deploy\local\.env.local -f deploy\local\docker-compose.yml"
iex "$c run --rm terrific-catalogue-import python -m app.scripts.import_odoo_catalogue --validate"
iex "$c run --rm terrific-catalogue-import python -m app.scripts.import_odoo_catalogue --plan"
iex "$c run --rm terrific-catalogue-import python -m app.scripts.import_odoo_catalogue --apply --confirm-import"
iex "$c run --rm terrific-catalogue-import python -m app.scripts.import_odoo_catalogue --reconcile"
```

A finished import doesn't prove the records exist. Check them in Odoo directly:

```powershell
iex "$c exec -T terrific-postgres psql -U terrific_odoo -d terrific_odoo -c 'select count(*) from product_template; select count(*) from product_product;'"
```

## Backup and restore

From Git Bash:

```bash
deploy/scripts/backup-all.sh local
deploy/scripts/verify-backup.sh deploy/local/backups/full-<timestamp>-manual
```

`verify-backup.sh` restores into a throwaway container with no network and prints row counts
to compare with the source.
