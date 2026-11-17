# Staging deployment and test plan

> **Optional.** The chosen approach updates the live site directly, without a separate staging
> environment: see [update-plan.md](update-plan.md). This plan is kept for if a staging copy
> is wanted later.

For whoever carries out the staging deployment. **Not approved yet.** It starts only after
[VPS discovery](vps-access-and-discovery.md) is complete and this plan has been approved.

Staging runs the Stage A demo configuration on the VPS, completely separate from production
and from every other application. Stop at the first failure in any step, and see "Stop
conditions" at the end.

## Layout

| Part | Value |
|---|---|
| Directory | `/opt/terrific-bites-staging` |
| Compose project | `terrific-bites-staging` (set by `COMPOSE_PROJECT_NAME`) |
| API | `https://api.staging.terrific-bites.trunexus.ai`, on `127.0.0.1:18011` |
| Frontend | `https://staging.terrific-bites.trunexus.ai`, on `127.0.0.1:18020` |
| Cookie domain | `staging.terrific-bites.trunexus.ai` |
| Stage | `DEPLOYMENT_STAGE=demo`. All providers are stubs and Odoo values stay blank |

The staging frontend is the production build run in Cloudflare's `workerd` runtime in a
temporary container on the VPS. That keeps the same runtime and the same two-hostname layout
as production without publishing anything from Lovable. Lovable's own build is tested
separately in step 10.

## Changes that need approval

| Step | Change | Effect on other applications |
|---|---|---|
| 1 | Two `A` records: `staging.terrific-bites` and `api.staging.terrific-bites` → `187.127.159.23` | None. New names only |
| 3 | New containers, networks and volumes under the `terrific-bites-staging` project | Uses CPU, memory and disk. Limits are set, and step 8 measures the effect |
| 6 | Two new Caddy site blocks, then a Caddy reload | Caddy is shared. A reload is graceful, and the config is validated first |

## Before each step

Compare with the discovery baseline after every step that changes the server:

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -v terrific-bites | sort > /tmp/now.txt
diff <(grep -v terrific-bites baseline-containers.txt | sort) /tmp/now.txt
# Plus: curl -s -o /dev/null -w '%{http_code}\n' https://<each existing site>
```

## Steps

### 1. DNS
Add the two records. **Pass:** both names resolve to `187.127.159.23`, and
`terrific-bites.trunexus.ai` still resolves to `185.158.133.1`.

### 2. Docker build
```bash
sudo mkdir -p /opt/terrific-bites-staging && sudo chown "$USER" /opt/terrific-bites-staging
cd /opt/terrific-bites-staging
git clone <repo> . && git checkout <approved-sha>
cd deploy
docker build -f backend.Dockerfile -t "terrific-bites-api:$(git rev-parse HEAD)" ..
```
**Pass:** the build succeeds, and `docker run --rm <image> id` shows `uid=10001`.

### 3. Compose startup
```bash
export COMPOSE_PROJECT_NAME=terrific-bites-staging
cp .env.prod.example .env.prod && chmod 600 .env.prod
```
Fill in new secrets (`openssl rand -hex 32`, one per secret), and the staging hostnames from
the layout table. Set `API_HOST_PORT=18011`.
```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet
scripts/migrate.sh
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --no-build --wait
```
Then make the scripts executable if the checkout lost the mode bits: `chmod +x scripts/*.sh`.

**Pass:** all services are healthy, and only `127.0.0.1:18011` is published:
`docker ps --filter name=terrific-bites-staging --format '{{.Names}} {{.Ports}}'`.

**Also confirm the safety refusal:** run the API once with `ADMIN_JWT_SECRET` blank. It must
refuse to start, naming the setting without printing any value.

### 4. Database migration
```bash
COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"
$COMPOSE run --rm migrate alembic current    # 0016 (head)
scripts/migrate.sh                           # re-run: no change, still at head
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --dry-run
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply   # re-run: nothing new
```
**Pass:** the database is at head, and the second seed run changes nothing.

### 5. Backup and restore
```bash
Q='select name_en from categories where slug = $$cakes$$'
scripts/backup-db.sh staging-test
$COMPOSE exec -T postgres psql -U terrific_bites -d terrific_bites -tc "$Q"
# Change something the backup must bring back.
$COMPOSE exec -T postgres psql -U terrific_bites -d terrific_bites -c \
  "update categories set name_en = 'RESTORE TEST' where slug = 'cakes'"
scripts/restore-db.sh backups/<the-dump>      # type RESTORE when asked
$COMPOSE exec -T postgres psql -U terrific_bites -d terrific_bites -tc "$Q"
```
**Pass:** the name goes back to its original value, and the API comes back healthy. These
scripts have never been run, because Docker wasn't available during local testing. This step
runs only against the staging database, so check the working directory and
`COMPOSE_PROJECT_NAME` first.

### 6. HTTPS and Caddy
Copy `deploy/caddy/api.terrific-bites.caddy` to a staging version: change the hostname to
`api.staging...`, the port to `18011`, and the log path. Add a similar block for
`staging.terrific-bites.trunexus.ai` → `127.0.0.1:18020`. If Caddy runs in a container, see
"Before the first deployment" in the runbook.
```bash
caddy validate --config /etc/caddy/Caddyfile      # must pass before reloading
sudo systemctl reload caddy
```
**Pass:** certificates are issued, `curl -I` shows HTTP/2 200 on both names, and every existing
site still matches the baseline.

### 7. Frontend and API communication
Build on a development machine and copy the output to the VPS:
```bash
VITE_API_BASE_URL=https://api.staging.terrific-bites.trunexus.ai npm run build
grep -rl 'localhost:80' .output/public/assets   # must find nothing
scp -r .output <user>@187.127.159.23:/opt/terrific-bites-staging/frontend-output
```
Run it on the VPS:
```bash
docker run -d --name terrific-bites-staging-frontend --restart unless-stopped \
  --memory 512m -p 127.0.0.1:18020:8787 -v "$PWD/../frontend-output:/site:ro" \
  -w /site/server node:22-slim \
  npx --yes wrangler@4 dev --config wrangler.json --ip 0.0.0.0 --port 8787 \
  --persist-to /tmp/wrangler-state
```
**Pass:** the storefront loads over HTTPS, the browser console has no CORS errors, and
`scripts/smoke.sh https://api.staging.terrific-bites.trunexus.ai` passes with
`FRONTEND_ORIGIN=https://staging.terrific-bites.trunexus.ai`.

### 8. Functional tests
Use a real browser, in English and Arabic, on desktop and at phone width.

| Area | Test | Pass |
|---|---|---|
| Catalogue | Home, shop, each category, product page | 26 products. No console or hydration errors |
| Variants | Change size and flavour | The price follows the selected variant |
| Checkout | Sign in, customize, delivery, payment, confirm | Order created, labelled `DEMO-` |
| Refresh | Refresh on the payment page | Product name and image stay |
| Demo payment | Payment page | Demo notice shown, no card fields, button says "Place demo order" |
| Demo sign-in | Login and signup | Demo notice shown |
| Admin | Log in | Cookies on the shared domain, `admin_csrf` readable by the page |
| Admin CSRF | Save a setting and change an order's status | Succeeds. Removing the CSRF header gets a 403 |
| Arabic | Switch language on every page above | Right-to-left layout, translated notices, nothing cut off |
| Tracking | Open the tracking link | Works. Replacing the token gets a 404 |

### 9. Order lifecycle, Odoo and monitoring
```bash
$COMPOSE exec -T postgres psql -U terrific_bites -d terrific_bites -c \
  "select order_number,is_demo,status,odoo_sync_status,odoo_sale_order_id from orders"
$COMPOSE exec -T postgres psql -U terrific_bites -d terrific_bites -c \
  "select event_type,status,count(*) from order_outbox_events group by 1,2"
$COMPOSE exec -T api python -m app.scripts.requeue_stub_synced_orders --dry-run
$COMPOSE exec -T api python -m app.scripts.ops_health_check
```
**Pass:**
- Orders show `is_demo=true`, `simulated`, and no Odoo id. Admin shows "simulated (not in Odoo)".
- No `order.created` event is pending.
- The requeue dry run reports no orders.
- The health check is `ok`.

**Then test the alerts**, staging containers only. Set the email settings (or a webhook) in
`.env.prod`, run `scripts/monitor.sh --test-alert`, and confirm the message arrived at the agreed
address, checking spam. Then:
```bash
$COMPOSE stop celery-worker        # within about 5 minutes the monitor must alert once
scripts/monitor.sh; scripts/monitor.sh
$COMPOSE start celery-worker       # the next run must send one recovery message
```

**Measure performance.** A single fast result proves nothing, so run this at quiet and busy times:
```bash
scripts/measure-product-page.sh https://staging.terrific-bites.trunexus.ai/product/buttercream-cake 20 30 3
```
**Pass:** no sample over 3 seconds. Investigate any `connect` time near 21 seconds. Also record
`docker stats` and confirm the existing applications' memory and response times match the
baseline. This does not measure Lovable's hosting, which step 10 covers.

### 10. Lovable build
Lovable picks up pushed commits, and `.env.production` points the frontend at the production
API. So this step needs the production API running first and needs its own approval. **It
isn't part of staging sign-off.** After publishing, run the same measurement against
`https://terrific-bites.trunexus.ai/product/buttercream-cake`.

### 11. Final regression and teardown
Compare every existing site and container with the baseline. Then either keep staging for
later releases or remove it:
```bash
docker rm -f terrific-bites-staging-frontend
docker compose --env-file .env.prod -f docker-compose.prod.yml down      # add -v only to delete staging data
```
Remove the Caddy blocks, reload Caddy, and delete the two DNS records.

## Stop conditions

Stop and report without trying to fix it in place if:
- any existing application's container status or response differs from the baseline;
- memory or disk use would leave less than 500 MB of RAM or 10% of disk free;
- `caddy validate` fails, or a certificate can't be issued;
- a command would touch anything outside the `terrific-bites-staging` project;
- any order, log or alert contains a real customer's details;
- anything attempts to contact Odoo.
