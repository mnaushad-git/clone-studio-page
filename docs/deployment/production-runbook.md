# Production runbook — Terrific Bites backend

For whoever deploys or operates the backend. Every step below that changes the VPS, DNS or
the live site needs approval first.

## Layout

| Part | Where | Notes |
|---|---|---|
| Frontend | Lovable, `https://terrific-bites.trunexus.ai` | Reads `VITE_API_BASE_URL` from `.env.production` at build time |
| API | VPS, `https://api.terrific-bites.trunexus.ai` | Published on loopback only, port `API_HOST_PORT` |
| TLS | The VPS's existing Caddy | `deploy/caddy/api.terrific-bites.caddy` |
| PostgreSQL, Redis, Celery | Containers in the `terrific-bites` Compose project | Internal network, not published, not shared with other applications |

The stage is fixed to `demo` (Stage A) in `deploy/docker-compose.prod.yml`, along with `stub`
for Odoo order push, payments and notifications, so `.env.prod` cannot switch them. The app
refuses to start if the stage and providers disagree. See
[production-readiness-checklist.md](production-readiness-checklist.md) for what each stage
requires, and [staging-plan.md](staging-plan.md) for the test plan that comes first.

## Before the first deployment

1. Run `deploy/scripts/vps-discovery.sh` (read-only) and confirm there is enough capacity
   and that port 18010 is free. If it isn't, change `API_HOST_PORT` and the Caddy block.
2. Find out how Caddy runs:
   - **On the host:** the provided block works as written.
   - **In a container:** `127.0.0.1` means the Caddy container itself. Use the host gateway
     address as the upstream instead. Don't attach Caddy to the Terrific Bites networks.
3. Add the DNS record in hPanel (trunexus.ai → DNS): type `A`, name `api.terrific-bites`,
   value `187.127.159.23`, TTL 600. Leave every other record alone.
4. Confirm in Lovable which branch it builds. Don't publish yet.

## First deployment

Run on the VPS from `/opt/terrific-bites`:

```bash
git clone <repo> . && git checkout <approved-sha>
cd deploy
cp .env.prod.example .env.prod && chmod 600 .env.prod
# Fill in the secrets (openssl rand -hex 32, one per secret).
# Set TB_IMAGE_TAG to the SHA.

docker build -f backend.Dockerfile -t "terrific-bites-api:$(git rev-parse HEAD)" ..
scripts/migrate.sh

COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --dry-run
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply
$COMPOSE run --rm migrate python -m app.scripts.create_admin_user \
  --email <owner-email> --full-name "<name>" --role SUPER_ADMIN

$COMPOSE up -d --no-build --wait
```

Then, with approval, add the Caddy block:

```bash
caddy validate --config /etc/caddy/Caddyfile   # must pass
systemctl reload caddy                         # graceful; other sites keep serving
scripts/smoke.sh                               # from the deploy directory
```

For the minimal path from today's live site, see [update-plan.md](update-plan.md).

Publish the frontend only after the smoke test passes. Before that the live site would
point at an API that doesn't exist yet.

```bash
npm run build && node scripts/check-prod-bundle.mjs   # on the commit Lovable will build
```

Finally, schedule the nightly backup and the monitor (`crontab -e`):

```
15 2 * * * /opt/terrific-bites/deploy/scripts/backup-db.sh nightly >> /var/log/terrific-bites-backup.log 2>&1
*/5 * * * * /opt/terrific-bites/deploy/scripts/monitor.sh >> /var/log/terrific-bites-monitor.log 2>&1
```

## Updating

```bash
git fetch && git checkout <sha>
cd deploy
docker build -f backend.Dockerfile -t "terrific-bites-api:$(git rev-parse HEAD)" ..
# Note the current TB_IMAGE_TAG (it is the rollback target), then set the new one in .env.prod
scripts/migrate.sh
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --no-build --wait
scripts/smoke.sh
```

## Migrations

`scripts/migrate.sh` backs up, applies `alembic upgrade head`, and confirms the database is
at head. It is safe to re-run. Keep migrations backward compatible with the previous image
so that the application can be rolled back without touching data.

## Rollback

**Application only (no migration, or a backward-compatible one).** Set `TB_IMAGE_TAG` back
to the previous SHA in `.env.prod`, then:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --no-build --wait
scripts/smoke.sh
```

**Application and database (an incompatible migration).** Set the previous tag as above,
then run `scripts/restore-db.sh backups/<pre-migrate-dump>`. Orders placed since that backup
are lost, so export them first and decide what to do with them.

**Frontend.** Restore the previous version in Lovable. The current live version doesn't use
the API, so it's the safe fallback.

**Removing the API from the VPS.** Remove the Caddy block, reload Caddy, then run
`docker compose ... down`. Keep the volumes unless you intend to delete the data: `down -v`
destroys the database. Delete the DNS record.

Other applications are not involved in any of these steps. Never run
`docker system prune` on this server, because it can remove other applications' resources.

## Backups

`scripts/backup-db.sh` writes verified dumps to `deploy/backups/` and keeps the newest 14.
**They are on the same server as the database**, so losing the VPS loses them too. An
off-site copy is still needed before real orders are taken. Test `restore-db.sh` on a
non-production copy, because an untested backup can't be relied on.

## Secrets

Secrets live only in `deploy/.env.prod` on the server (git-ignored, mode 600). Generate new
ones for production; don't reuse values from any `.env` on a development machine or from
another application. The app refuses to start in production on default or unsafe settings,
and names the setting without printing its value.

To rotate:
- `ADMIN_JWT_SECRET`: change it and restart. Admins have to sign in again.
- `REDIS_PASSWORD`: change it and recreate the containers.
- `POSTGRES_PASSWORD`: the value in `.env.prod` only applies when the volume is first
  created, so first run `ALTER USER terrific_bites PASSWORD '...'` in the database.

## Going live with Odoo order push

Needs explicit approval, and is part of moving to `DEPLOYMENT_STAGE=live`. Change the stage
and providers in `deploy/docker-compose.prod.yml` and set the Odoo values in `.env.prod`.

Until then, orders are recorded as `simulated`: nothing was sent to Odoo. Demo orders stay
that way permanently and can't be sent. Any non-demo order simulated by the stub can be sent
with `app.scripts.requeue_stub_synced_orders` (start with `--dry-run`).

## Monitoring

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=100 api
```

Logs rotate at 10 MB, five files per container. `GET /api/v1/readiness` returns 503 when
PostgreSQL or Redis is unreachable, and Docker marks the API unhealthy after three failed
checks.

`scripts/monitor.sh` runs every five minutes and alerts once when the state changes, and once
on recovery. It sends to every channel set in `.env.prod`: email through an SMTP mailbox (see
[vps-access-and-discovery.md](vps-access-and-discovery.md) for Hostinger's settings) and/or
`ALERT_WEBHOOK_URL` (Slack, Discord, or any endpoint accepting a JSON POST). If a channel fails,
the alert is retried on the next run. Check a new channel with `scripts/monitor.sh --test-alert`,
then confirm the message actually arrived: the mail server accepting it isn't proof of delivery.

It checks:
- containers are running and healthy, and the public health URL responds;
- the worker heartbeat, which goes stale if Beat or the worker stops;
- paid orders waiting over 15 minutes, and failed order events;
- disk use, and the age of the newest backup.

To run the application's part by hand:
`docker compose ... exec -T api python -m app.scripts.ops_health_check`.

**The monitor runs on the VPS, so it can't report the VPS going down.** Add an external uptime
check on `https://api.terrific-bites.trunexus.ai/api/v1/health` as well.

## Page timing

`scripts/measure-product-page.sh <url>` takes repeated samples with gaps between them. An
intermittent 21-second page load seen during local testing came from a test hostname: DNS64
returned an IPv6 address that couldn't be reached, and Windows spends 21 seconds timing out
before falling back to IPv4. That explains the local result only, so hosted timing still has
to be measured with this script. If a `connect` time near 21 seconds shows up, check for a
wrong `AAAA` record on the API hostname.
