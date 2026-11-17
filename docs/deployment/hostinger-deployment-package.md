# Hostinger staging deployment

Deploys the whole of Terrific Bites (storefront, Admin Portal, API, workers, PostgreSQL, Redis
and a staging Odoo 19) to the dedicated Hostinger KVM 4 VPS with Docker Compose, as the
client-facing **staging** environment for demonstration, testing and UAT.

| | |
|---|---|
| VPS | Hostinger KVM 4, dedicated, Ubuntu 24.04, `2.25.11.35` |
| Storefront and Admin | `https://terrific-bites.trunexus.ai` (client staging) |
| API | `https://api.terrific-bites.trunexus.ai` (staging API) |
| Stage | `DEPLOYMENT_STAGE=staging`, frontend built with `VITE_DEMO_MODE=true` |
| Branch | `deployment/terrific-bites-hostinger` (never the Lovable baseline branch) |

**Status: prepared, and not yet run anywhere.** No image has been built and no service started.
Treat the first run as the Docker validation and stop at the first failure.

The VPS runs nothing else, so the old shared-VPS constraints (myMakan, Maskan, an existing Caddy,
no Docker group) no longer apply. The Lovable-hosted staging site keeps serving
`terrific-bites.trunexus.ai` until the cutover, which needs explicit approval.

## What staging may and may not do

| | Staging behaviour | Enforced by |
|---|---|---|
| Payments | Stub only. The frontend shows the demo payment notice and collects no card details | `PAYMENT_PROVIDER: stub` in Compose; `_check_staging` refuses anything else |
| Notifications | Stub only. No email or SMS reaches a customer | `NOTIFICATION_PROVIDER: stub`; `_check_staging` |
| Orders | Real test orders (`TB-…`, not `is_demo`). Paid by the stub, then pushed to the staging Odoo as sale orders | `ODOO_ORDER_PUSH_PROVIDER: live` in Compose |
| Odoo | Only this stack's own `odoo` container, database `terrific_odoo` | See the safeguards below |
| Catalogue import | Refused unless separately approved, and then only test data into the staging Odoo | `ODOO_WRITE_APPROVED_TARGET` blank by default |

### Staging Odoo safeguards

1. **Fixed address.** `http://odoo:8069` and `terrific_odoo` are constants in
   `backend/app/core/config.py` (`STAGING_ODOO_*`) and hard-coded in `docker-compose.prod.yml`.
   `.env.prod` can't change them.
2. **Fails closed at startup.** With `DEPLOYMENT_STAGE=staging` every process refuses to start
   if any of these is wrong: a non-stub payment or notification provider; any other Odoo URL
   or database (including the VPS IP, `localhost`, `https`, another port or an external host);
   any other write-approval target; an Odoo credential on the API, Beat or migrations; or a
   login other than `terrific-order-sync` (worker) or `terrific-catalogue-import` (import).
   The worker also refuses to start without its credential and approval. Error messages name
   the setting, never its value.
3. **Checked again at use.** `OdooConfig.from_settings` won't build any Odoo client, read or
   write, for another instance on staging. `assert_odoo_write_target_approved` refuses a
   write to anything but `http://odoo:8069#terrific_odoo`, even if it is "approved".
4. **No route out.** The worker and the catalogue import, the only holders of Odoo logins,
   are on the `internal` Docker network only, with no route off the host. They can't reach
   an external or production Odoo even if the code were changed.
5. **Least-privilege users.** `deploy/odoo/bootstrap.py` creates the order-sync user (sales
   only, can't create products) and the import user. The pusher refuses an administrator
   account. The `terrific_order_sync` addon enforces one sale order per storefront order.
6. **Test data only.** The staging Odoo starts empty. It only ever holds the catalogue from
   `data/catalogue/` and test orders placed on staging. Never restore a production dump into it.

Tests: `backend/tests/unit/test_staging_settings.py` (configurations permitted and refused,
the in-use checks, and that every Compose service is a valid staging process) and
`backend/tests/integration/test_staging_order_flow.py` (checkout, stub payment, outbox, push,
retry and idempotency).

## Contents

| Item | Location |
|---|---|
| Compose file | `deploy/docker-compose.prod.yml` |
| Images | `deploy/frontend.Dockerfile`, `deploy/backend.Dockerfile` |
| Staging Odoo | `deploy/odoo/` (config template, entrypoint, bootstrap, `terrific_order_sync` addon) |
| PostgreSQL initialisation | `deploy/postgres-init/01-create-databases.sh` |
| Caddy sites | `deploy/caddy/api.terrific-bites.caddy`, `terrific-bites.caddy`, `preview.terrific-bites.caddy` |
| Environment template | `deploy/.env.prod.example` |
| Scripts | `deploy/scripts/` (`migrate`, `smoke`, `monitor`, `backup-all`, `verify-backup`, `restore-db`) |

## 1. Prepare the server

Who runs what: the root steps (firewall, `/opt` directory, Caddy) run as root in the hPanel
browser terminal; everything else runs as the `tb-deploy` user, in the `docker` group once that
is approved (see [vps-access-and-discovery.md](vps-access-and-discovery.md)). The `sudo`
prefixes below are for root steps run from another account.

Read-only first: run `deploy/scripts/vps-discovery.sh`, as in
[vps-access-and-discovery.md](vps-access-and-discovery.md), and check:

- Docker Engine and the Compose plugin work (`docker compose version`).
- About 4.5 GB of RAM is free (the Compose memory limits add up to about 4.3 GB) and at least
  25 GB of disk.
- Ports 80 and 443 are free, and 18010, 18011 and 18069 are free on loopback.

Firewall. Allow only SSH, HTTP and HTTPS, in hPanel's VPS firewall and on the host:

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable && sudo ufw status
```

Every container port is published on `127.0.0.1` only, so nothing else is reachable from
outside. Docker bypasses ufw for published ports, which is why none is published publicly.

Code. Give the server a read-only GitHub deploy key for the repository, then:

```bash
sudo mkdir -p /opt/terrific-bites && sudo chown tb-deploy:tb-deploy /opt/terrific-bites   # root step
git clone --branch deployment/terrific-bites-hostinger <repository-ssh-url> /opt/terrific-bites
cd /opt/terrific-bites && git checkout <approved-sha>
```

## 2. Install Caddy

Caddy runs on the host as a systemd service, from Caddy's official apt repository:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

Replace the default Caddyfile, which serves a placeholder page on port 80, with one that only
imports the site files:

```bash
sudo mkdir -p /etc/caddy/sites
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.default
printf '{\n\temail <ops-email>\n}\n\nimport /etc/caddy/sites/*.caddy\n' | sudo tee /etc/caddy/Caddyfile
```

Add site files only when the stage below says so. After each change:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

Caddy gets each certificate from Let's Encrypt once that hostname's DNS points at the VPS, so
adding a site before its DNS record is harmless but stays without a certificate.

## 3. Environment

```bash
cd /opt/terrific-bites/deploy
cp .env.prod.example .env.prod && chmod 600 .env.prod
```

Fill in `.env.prod` and set `TB_IMAGE_TAG` to the approved SHA. Generate every secret
separately with `openssl rand -hex 32`, and use new, staging-only Odoo passwords, never ones
from any other Odoo. Every variable must be set, including those only one-shot services use,
because Compose checks all of them on every command. `.env.prod` stays on the server and is
git-ignored. Leave `ODOO_WRITE_APPROVED_TARGET` blank.

## 4. Build and start

```bash
cd /opt/terrific-bites/deploy
SHA=$(git rev-parse HEAD)
docker build -f backend.Dockerfile -t terrific-bites-api:$SHA ..
docker build -f frontend.Dockerfile \
  --build-arg VITE_API_BASE_URL=https://api.terrific-bites.trunexus.ai \
  --build-arg VITE_DEMO_MODE=true \
  -t terrific-bites-frontend:$SHA ..

# The bundle must call the staging API, never localhost.
docker run --rm --entrypoint sh terrific-bites-frontend:$SHA -c \
  'grep -rl "api.terrific-bites.trunexus.ai" .output/public | head -1; ! grep -rl "localhost:8020" .output/public'

COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"
$COMPOSE up -d --wait postgres redis
scripts/migrate.sh
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply
```

### Staging Odoo

```bash
$COMPOSE run --rm odoo-init                                          # creates terrific_odoo, installs modules
$COMPOSE run --rm -T odoo-init shell --no-http < odoo/bootstrap.py    # SAR, 15% VAT, integration users
$COMPOSE up -d --wait odoo
docker image inspect odoo:19.0 --format '{{index .RepoDigests 0}}'   # record it and pin the image
```

`odoo-init` installs `sale_management`, `stock`, `account`, `website_sale` and
`terrific_order_sync`. The bootstrap is idempotent and prints the two integration users' IDs,
the currency, the pricelist and the VAT setup. The Odoo web client is on `127.0.0.1:18069`
only: open it through an SSH tunnel (`ssh -L 18069:127.0.0.1:18069 <user>@2.25.11.35`) and sign
in with the database master password from `.env.prod` only to manage the database.

### Admin user and the full stack

```bash
$COMPOSE run --rm migrate python -m app.scripts.create_admin_user \
  --email <owner-email> --full-name "<name>" --role SUPER_ADMIN
$COMPOSE up -d --no-build --wait
$COMPOSE ps
curl -s -H 'Host: api.terrific-bites.trunexus.ai' http://127.0.0.1:18010/api/v1/readiness
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18011/
```

Every container must be healthy (Beat has no health check; the worker heartbeat covers it),
readiness must return 200, and the storefront 200.

## 5. Staging catalogue in Odoo (approval required)

Orders can only be pushed for products that exist in Odoo, so order sync needs the catalogue
imported into the staging Odoo first. This writes test data into the staging Odoo only, and it
needs approval like any import. Set `ODOO_WRITE_APPROVED_TARGET=http://odoo:8069#terrific_odoo`
in `.env.prod` (staging refuses any other value), then:

```bash
IMPORT="$COMPOSE run --rm catalogue-import python -m app.scripts.import_odoo_catalogue"
$IMPORT --validate
$IMPORT --plan --output /tmp/plan.json
$IMPORT --apply --confirm-import --output /tmp/apply.json
$IMPORT --reconcile --output /tmp/reconcile.json   # must report CLEAN and 55 of 55 prices
$COMPOSE exec celery-worker celery -A app.workers.celery_app call \
  app.workers.tasks.catalogue_sync.sync_catalogue_from_odoo \
  --kwargs '{"full_resync": true, "trigger": "MANUAL", "initiated_by": "deploy"}'
```

Clear `ODOO_WRITE_APPROVED_TARGET` again afterwards. `--output` must be under `/tmp` because
the image can't write elsewhere. Re-running is safe: a size price is set only while Odoo
still has it at zero. To change a price later, update `data/catalogue/products.json` and
redeploy first, then change Odoo, or the sync refuses to publish.

## 6. API site and pre-cutover validation (approval required)

DNS records, all new names, so the Lovable site is unaffected:

| Record | Value | When |
|---|---|---|
| `api.terrific-bites` A | `2.25.11.35` | Before the API site |
| `preview.terrific-bites` A | `2.25.11.35` | Before the preview site; removed after cutover |

Then install the API and preview sites:

```bash
sudo cp /opt/terrific-bites/deploy/caddy/api.terrific-bites.caddy /etc/caddy/sites/
sudo cp /opt/terrific-bites/deploy/caddy/preview.terrific-bites.caddy /etc/caddy/sites/
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

Add `https://preview.terrific-bites.trunexus.ai` to `CORS_ALLOWED_ORIGINS` in `.env.prod`
(comma-separated), then `$COMPOSE up -d --no-build --wait api`. The admin cookie domain
`terrific-bites.trunexus.ai` already covers the preview hostname.

### Validation

Run `scripts/smoke.sh` (expects `deployment_stage` `staging`), then on
`https://preview.terrific-bites.trunexus.ai`:

| Journey | Pass |
|---|---|
| Storefront | Home, shop, every category and product pages load in English and Arabic, RTL correct. Berry Truffle LARGE BOX shows SAR 14.38. Footer logo and images load |
| Checkout | Cart, minimum-order notice, delivery, promo code. The payment page shows the demo notice and no card form. The order confirms as `TB-…` |
| Order sync | In Admin, the order shows Odoo sync `synced` within a minute. Through the SSH tunnel, Odoo has one confirmed sale order with the same total, VAT and lines, in SAR |
| Retry | `$COMPOSE stop odoo`, place an order (it shows sync pending/failed), `$COMPOSE start odoo`; it syncs once, with no duplicate sale order |
| Admin | Sign in, orders, status changes, products, promo codes, content, catalogue sync runs, system status (payments `stub`, notifications `stub`, order push `live`) |
| No real side effects | No email or SMS received; no payment provider contacted |
| Isolation | `docker compose exec celery-worker python -c "import urllib.request as u; u.urlopen('https://example.com', timeout=5)"` fails |

Record results, then stop for approval of the cutover.

## 7. Backups and monitoring

```bash
scripts/backup-all.sh prod first
scripts/verify-backup.sh backups/<directory>       # compare the row counts with the source
scripts/monitor.sh --test-alert                    # confirm the alert arrives
```

Cron (`crontab -e` as the deploying user):

```
*/5 * * * * /opt/terrific-bites/deploy/scripts/monitor.sh >> /var/log/terrific-bites-monitor.log 2>&1
30 2 * * * /opt/terrific-bites/deploy/scripts/backup-all.sh prod nightly >> /var/log/terrific-bites-backup.log 2>&1
0 4 * * 0 /opt/terrific-bites/deploy/scripts/verify-backup.sh "$(ls -d /opt/terrific-bites/deploy/backups/*nightly | tail -1)" >> /var/log/terrific-bites-backup.log 2>&1
```

Also take an hPanel snapshot before the first deployment and before each upgrade, and set an
external uptime check on `https://api.terrific-bites.trunexus.ai/api/v1/health`, since
`monitor.sh` can't report the VPS itself going down.

Backups on the VPS don't survive losing the VPS. Copy each one off the server, encrypted with
a key that isn't stored there:

```bash
tar -C backups -cf - full-<timestamp>-nightly | age -r <public-key> > full-<timestamp>.tar.age
rclone copy full-<timestamp>.tar.age <remote>:terrific-bites-backups/
```

The off-site destination (for example Backblaze B2 or Hostinger Object Storage) is still an
open decision.

## 8. Cutover (approval required)

1. A day ahead, lower the TTL on the `terrific-bites` record.
2. Install the storefront site:
   `sudo cp /opt/terrific-bites/deploy/caddy/terrific-bites.caddy /etc/caddy/sites/`, validate,
   reload.
3. Repoint `terrific-bites` to `2.25.11.35`. Caddy issues the certificate once it resolves.
4. Repeat the storefront, checkout and Admin checks on `https://terrific-bites.trunexus.ai`.
5. After an agreed clean period, remove the preview site, its DNS record and its CORS origin.

## Updates

```bash
cd /opt/terrific-bites && git fetch && git checkout <new-approved-sha> && cd deploy
scripts/backup-all.sh prod pre-release
# Rebuild both images with the new SHA as in section 4, set TB_IMAGE_TAG to it in .env.prod, then:
scripts/migrate.sh
$COMPOSE up -d --no-build --wait && scripts/smoke.sh
```

## Rollback

| Situation | Action |
|---|---|
| Bad release, no schema change | Set `TB_IMAGE_TAG` to the previous SHA, then `$COMPOSE up -d --no-build --wait` |
| Bad migration or data | `scripts/restore-db.sh <dump>` from the `app.dump` taken before the release |
| Staging Odoo damaged | Stop `odoo`, restore `odoo.dump` with `pg_restore --clean --if-exists -U terrific_odoo`, extract `odoo-filestore.tar.gz` into `/var/lib/odoo`, start `odoo` |
| Whole VPS | Restore the hPanel snapshot |
| Site unusable after cutover | Point the `terrific-bites` record back to Lovable |

Lovable keeps serving staging until its record moves, so don't retire it until the VPS has run
cleanly for an agreed period.
