#!/usr/bin/env bash
# Full backup: application database, Odoo database, Odoo filestore and product media, plus
# checksums. Safe to run while the site is up.
#
#   deploy/scripts/backup-all.sh local|prod [label]
#
# The dumps hold no connection secrets, and no .env file is ever included. The Odoo dump
# does hold hashed user passwords and customer data, so encrypt it before it leaves the
# machine (see "Off-site backups" in docs/deployment/hostinger-deployment-package.md).
set -euo pipefail

STACK="${1:?usage: backup-all.sh local|prod [label]}"
LABEL="${2:-manual}"
[[ "$LABEL" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "invalid label: $LABEL" >&2; exit 2; }

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
case "$STACK" in
  local)
    compose() { docker compose --env-file "$DEPLOY_DIR/local/.env.local" -f "$DEPLOY_DIR/local/docker-compose.yml" "$@"; }
    PG=terrific-postgres; ODOO=terrific-odoo; API=terrific-api
    BACKUP_ROOT="${BACKUP_DIR:-$DEPLOY_DIR/local/backups}"
    ;;
  prod)
    compose() { docker compose --env-file "$DEPLOY_DIR/.env.prod" -f "$DEPLOY_DIR/docker-compose.prod.yml" "$@"; }
    PG=postgres; ODOO=odoo; API=api
    BACKUP_ROOT="${BACKUP_DIR:-$DEPLOY_DIR/backups}"
    ;;
  *) echo "unknown stack: $STACK" >&2; exit 2 ;;
esac
KEEP="${BACKUP_KEEP:-14}"

umask 077
mkdir -p "$BACKUP_ROOT"
target="$BACKUP_ROOT/full-$(date -u +%Y%m%dT%H%M%SZ)-$LABEL"
partial="$target.partial"
trap 'rm -rf "$partial"' EXIT
mkdir "$partial"

compose exec -T "$PG" pg_dump -U terrific_bites -d terrific_bites -Fc --no-owner > "$partial/app.dump"
compose exec -T "$PG" pg_dump -U terrific_odoo -d terrific_odoo -Fc --no-owner > "$partial/odoo.dump"
compose exec -T "$ODOO" tar -C /var/lib/odoo -czf - filestore/terrific_odoo > "$partial/odoo-filestore.tar.gz"
compose exec -T "$API" tar -C /app -czf - media > "$partial/media.tar.gz"

# A dump that cannot be listed cannot be restored, so it doesn't count as a backup.
for dump in app odoo; do
  [[ -s "$partial/$dump.dump" ]] || { echo "empty dump: $dump" >&2; exit 1; }
  compose exec -T "$PG" pg_restore --list < "$partial/$dump.dump" > /dev/null
done
for archive in odoo-filestore media; do
  gzip -t "$partial/$archive.tar.gz"
done

(cd "$partial" && sha256sum app.dump odoo.dump odoo-filestore.tar.gz media.tar.gz > SHA256SUMS)
mv "$partial" "$target"
echo "backup written: $target ($(du -sh "$target" | cut -f1))"

ls -1dt "$BACKUP_ROOT"/full-* | grep -v '\.partial$' | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -rf -- "$old"
done
