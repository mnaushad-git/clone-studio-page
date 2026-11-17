# Updating the live site

> **Superseded (17 November 2026).** This describes the earlier plan for the shared VPS
> `187.127.159.23` (existing Caddy, myMakan and Maskan, Stage A `demo`). Terrific Bites client
> staging now runs on the dedicated VPS `2.25.11.35` with `DEPLOYMENT_STAGE=staging`. Follow
> [hostinger-deployment-package.md](hostinger-deployment-package.md) instead; this file is
> kept for its history only.

The shortest path from today's live site to the current code. It reuses the Lovable hosting
and the existing VPS and Caddy, and adds no new servers or environments.

## What's live today

| Part | Live | Source |
|---|---|---|
| Website | `https://terrific-bites.trunexus.ai`, hosted by Lovable (Cloudflare) | Published from `main` at `72983c7`, Arabic included |
| Backend | None. The site is frontend-only | No API in DNS, and the VPS answers for no Terrific Bites hostname |
| Data | Products are built into the site. Carts, sign-ins and order history live in each visitor's browser (`tb.state.v1`) | Nothing server-side to migrate |
| Supabase | Referenced in the code, but the project no longer resolves | Unused |

## What's new

`baseline-terrific-bites-storefront-and-admin-ui` is ahead of the live site by `01e40b1`,
`8ad113f`, `e58e072`, and the pending changes:

- **The backend API.** The website calls it for the catalogue, checkout, tracking and the
  Admin Portal, so the new frontend can't go live without it.
- **The Stage A demo labelling.** Demo banner, demo payment, `DEMO-` order numbers, and
  simulated Odoo sync.
- **The fixes and security work from the last three rounds.**

Visitors' saved carts and wishlists keep working, because the product IDs are the same 26 in
both versions.

## What changes

| Component | Change | Effect on anything else |
|---|---|---|
| Website | Publish the new commit in Lovable | Replaces the current version. Lovable keeps the old one to restore |
| VPS | One new Compose project in `/opt/terrific-bites`: API, worker, scheduler, PostgreSQL, Redis | Own containers, networks and volumes. Uses about 2.2 GB of RAM at its limits |
| Caddy | One new site block, then a validated, graceful reload | Other sites keep serving |
| DNS | One new `A` record: `api.terrific-bites` → `187.127.159.23` | None. The website's own record is unchanged |

## Steps

Each needs your go-ahead. Run them in order, and stop at the first failure.

### 1. Check the VPS (read-only)
Set up access and run discovery as in
[vps-access-and-discovery.md](vps-access-and-discovery.md). Continue only if:
- about 2.3 GB of RAM and 10 GB of disk are free;
- port 18010 is free;
- you know whether Caddy runs on the host or in a container.

### 2. Commit and push (local)
```bash
git push origin baseline-terrific-bites-storefront-and-admin-ui
```
**Don't publish in Lovable yet.** Pushing makes the change visible in the Lovable editor but
doesn't change the live site. If Lovable is connected to `main`, merge into `main` the same way
the earlier Lovable work arrived there.

### 3. Start the API on the VPS
```bash
sudo mkdir -p /opt/terrific-bites && sudo chown tb-deploy /opt/terrific-bites
cd /opt/terrific-bites
git clone https://github.com/mnaushad-git/clone-studio-page.git .
git checkout <the pushed commit>
cd deploy
cp .env.prod.example .env.prod && chmod 600 .env.prod
nano .env.prod   # new secrets (openssl rand -hex 32, one each), TB_IMAGE_TAG=<commit>, alert email

docker build -f backend.Dockerfile -t "terrific-bites-api:$(git rev-parse HEAD)" ..
scripts/migrate.sh
COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"
$COMPOSE run --rm migrate python -m app.scripts.seed_catalogue --apply
$COMPOSE run --rm migrate python -m app.scripts.create_admin_user \
  --email <owner-email> --full-name "<name>" --role SUPER_ADMIN
$COMPOSE up -d --no-build --wait
$COMPOSE ps                                    # all healthy
curl -s -H 'Host: api.terrific-bites.trunexus.ai' http://127.0.0.1:18010/api/v1/readiness
```
Nothing outside `/opt/terrific-bites` and the `terrific-bites` Compose project is touched. If
the repository is made private first, the clone needs a deploy key or token.

### 4. DNS (hPanel)
**Domains → trunexus.ai → DNS / Nameservers**. Add an `A` record: name `api.terrific-bites`,
points to `187.127.159.23`, TTL 600. Change no other record. Then check:
```powershell
nslookup api.terrific-bites.trunexus.ai 8.8.8.8
```

### 5. Caddy
Add `deploy/caddy/api.terrific-bites.caddy` to the existing Caddy configuration. If Caddy runs in
a container, use the host gateway address instead of `127.0.0.1`. Then:
```bash
caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
scripts/smoke.sh          # every line must say ok
```
Re-check that every other site on the server still responds as it did in the discovery report.

### 6. Publish in Lovable
Open the project in Lovable, confirm it shows the pushed commit, and click **Publish** (or
**Update**). Then, on the live site:
- browse the shop and a product;
- check a demo order goes through, with the demo banner showing;
- check you can sign in to `/admin`;
- confirm the network panel shows calls to `api.terrific-bites.trunexus.ai` and none to
  `localhost`.
```bash
scripts/measure-product-page.sh https://terrific-bites.trunexus.ai/product/buttercream-cake 10 30 3
```

### 7. Schedule backups and monitoring
```
15 2 * * * /opt/terrific-bites/deploy/scripts/backup-db.sh nightly >> /var/log/terrific-bites-backup.log 2>&1
*/5 * * * * /opt/terrific-bites/deploy/scripts/monitor.sh >> /var/log/terrific-bites-monitor.log 2>&1
```
Run `scripts/monitor.sh --test-alert`, and confirm the email arrives.

## Rollback

| Problem | Undo |
|---|---|
| The new website misbehaves | In Lovable, restore the previous version. The site goes back to today's frontend-only version, which doesn't need the API |
| The API misbehaves after publishing | Restore the previous Lovable version first, then fix the API, or stop it: `$COMPOSE stop` |
| A later API update breaks something | Set `TB_IMAGE_TAG` back to the previous commit, then `$COMPOSE up -d --no-build --wait`. If a migration ran, see "Rollback" in the runbook |
| Remove the backend completely | Remove the Caddy block and reload, run `$COMPOSE down` (keeping the volumes unless you mean to delete the data), and delete the DNS record |

Nothing in any rollback touches other applications, and no visitor data is lost: carts and
history are in visitors' browsers. Orders placed after the update are in the new database and
survive a website rollback.
