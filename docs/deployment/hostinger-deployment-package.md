# Hostinger deployment package

Moves the whole of Terrific Bites onto the existing VPS (`187.127.159.23`) with Docker Compose.
It replaces the Lovable hosting assumed in [update-plan.md](update-plan.md).

**Status: prepared, and not yet run anywhere.** None of the images or Compose services have been
built or started. Docker validation happens on the VPS after discovery, not on Windows, so treat
the first run below as that validation and stop at the first failure.

## Contents

| Item | Location |
|---|---|
| Production Compose file | `deploy/docker-compose.prod.yml` |
| Frontend and backend images | `deploy/frontend.Dockerfile`, `deploy/backend.Dockerfile` |
| Odoo configuration | `deploy/odoo/` |
| PostgreSQL initialisation | `deploy/postgres-init/01-create-databases.sh` |
| Worker and Redis configuration | Services in the Compose file |
| Caddy site blocks | `deploy/caddy/terrific-bites.caddy`, `deploy/caddy/api.terrific-bites.caddy` |
| Environment template | `deploy/.env.prod.example` |
| Migrations | `deploy/scripts/migrate.sh` |
| Catalogue import and checks | `app.scripts.import_odoo_catalogue`, `app.scripts.check_catalogue_import_approvals` |
| Health and monitoring | `deploy/scripts/smoke.sh`, `deploy/scripts/monitor.sh` |
| Backup and restore | `deploy/scripts/backup-all.sh`, `deploy/scripts/verify-backup.sh`, `deploy/scripts/restore-db.sh` |

`restore-db.sh` restores the application database only. To restore Odoo, see Rollback below.

## Before starting

Run `deploy/scripts/vps-discovery.sh` and continue only if all of these hold:

- Docker and Compose are present.
- About 4.5 GB of RAM is free. The memory limits add up to about 4.3 GB.
- At least 25 GB of disk is free.
- Ports 18010, 18011 and 18069 are free on loopback.
- You know whether Caddy runs on the host or in a container. In a container, `127.0.0.1` upstreams
  need changing.

## DNS

| Record | Change | When |
|---|---|---|
| `api.terrific-bites` A | Add, pointing to `187.127.159.23` | Before adding the API site block |
| `terrific-bites` | Repoint from Lovable to `187.127.159.23` | Last. This is the cutover |

Lower the TTL on the `terrific-bites` record a day ahead so that a rollback takes effect quickly.

## Deployment

```bash
cd /opt/terrific-bites && git checkout <approved-sha> && cd deploy
cp .env.prod.example .env.prod && chmod 600 .env.prod
# Fill in .env.prod, using a separate `openssl rand -hex 32` value for each secret.
SHA=$(git rev-parse HEAD)
docker build -f backend.Dockerfile -t terrific-bites-api:$SHA ..
docker build -f frontend.Dockerfile \
  --build-arg VITE_API_BASE_URL=https://api.terrific-bites.trunexus.ai \
  --build-arg VITE_DEMO_MODE=true \
  -t terrific-bites-frontend:$SHA ..

COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"
$COMPOSE up -d --wait postgres redis
scripts/migrate.sh
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply
$COMPOSE run --rm odoo-init
$COMPOSE run --rm -T odoo-init shell --no-http < odoo/bootstrap.py
$COMPOSE run --rm migrate python -m app.scripts.create_admin_user \
  --email <owner-email> --full-name "<name>" --role SUPER_ADMIN
$COMPOSE up -d --no-build --wait
scripts/smoke.sh
```

`odoo-init` installs the `terrific_order_sync` addon, which enforces one sale order per storefront
order, and `website_sale`, which the catalogue gallery images need. Odoo credentials reach only
`celery-worker` and the one-shot `catalogue-import`. The API and Beat refuse to start with one.

Then add both Caddy site blocks, run `caddy validate`, reload gracefully, and make the DNS changes.
Each of these needs explicit approval, because Caddy and DNS are shared.

Production order push is fixed to the stub in the Compose file, and Odoo writes stay refused while
`ODOO_WRITE_APPROVED_TARGET` is blank. Importing the catalogue into production Odoo needs separate
written authorization, as set out in
[odoo-catalogue-import.md](../integrations/odoo-catalogue-import.md).

## Initial catalogue import

Only with that authorization. Set `ODOO_WRITE_APPROVED_TARGET=http://odoo:8069#terrific_odoo` in
`.env.prod`, and clear it again afterwards. Always pass `--output` under `/tmp`, because the image
can't write to its default report location.

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

Then confirm Berry Truffle's LARGE BOX reads 14.38:

```bash
curl -s https://api.terrific-bites.trunexus.ai/api/v1/catalogue/products/choc-berry | grep -o '"price":"[0-9.]*"'
```

Running the import again is safe. It sets a size price only while Odoo still has it at zero, and
reports any other difference instead of overwriting it.

### Changing a price after go-live

The worker compares Odoo's selling price with `data/catalogue/products.json` for every approved
SKU and publishes nothing if one differs, so an intended change needs both sides updated:

1. Update the price in `data/catalogue/products.json`, and build and deploy the new image.
2. Change the price in Odoo.

Between the two, the catalogue sync is refused and the last good catalogue stays live. A refusal
appears in Admin under the catalogue sync runs, naming each variant with both prices, and
`monitor.sh` alerts on it.

## Off-site backups

Schedule `backup-all.sh prod nightly` from cron and run `verify-backup.sh` weekly. Backups on the
VPS don't protect against losing the VPS, so copy each one elsewhere after encrypting it with a key
that isn't stored on the VPS:

```bash
tar -C backups -cf - full-<timestamp>-nightly | age -r <public-key> > full-<timestamp>.tar.age
rclone copy full-<timestamp>.tar.age <remote>:terrific-bites-backups/
```

Choosing the off-site destination (for example Backblaze B2 or Hostinger Object Storage) is an
open decision, because it adds a new account and cost.

## Rollback

| Situation | Action |
|---|---|
| Bad release, no schema change | Set `TB_IMAGE_TAG` to the previous SHA, then `$COMPOSE up -d --no-build --wait` |
| Bad migration or data | `scripts/restore-db.sh <dump>` from the `app.dump` taken before the release |
| Odoo damaged | Stop `odoo`, restore `odoo.dump` with `pg_restore --clean --if-exists -U terrific_odoo`, extract `odoo-filestore.tar.gz` into `/var/lib/odoo` |
| Site unusable after cutover | Point the `terrific-bites` DNS record back to Lovable |

Lovable keeps serving the previous site until its DNS record moves, so don't retire it until the
VPS has run cleanly for an agreed period.
