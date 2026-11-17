#!/usr/bin/env bash
# Dumps the Terrific Bites database and keeps the newest copies. Safe to run while the
# site is live. Backups stay on this server until an off-site copy is arranged (see the
# runbook): they do not protect against losing the VPS.
#
#   deploy/scripts/backup-db.sh [label]
# Cron: 15 2 * * * /opt/terrific-bites/deploy/scripts/backup-db.sh nightly
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"
KEEP="${BACKUP_KEEP:-14}"
LABEL="${1:-manual}"
[[ "$LABEL" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "invalid label: $LABEL" >&2; exit 2; }

compose() { docker compose --env-file "$DEPLOY_DIR/.env.prod" -f "$DEPLOY_DIR/docker-compose.prod.yml" "$@"; }

umask 077
mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/terrific_bites-$(date -u +%Y%m%dT%H%M%SZ)-$LABEL.dump"
partial="$target.partial"
trap 'rm -f "$partial"' EXIT

compose exec -T postgres pg_dump -U terrific_bites -d terrific_bites -Fc > "$partial"

# A dump that cannot be listed cannot be restored, so don't count it as a backup.
compose exec -T postgres pg_restore --list < "$partial" > /dev/null
[[ -s "$partial" ]] || { echo "empty dump" >&2; exit 1; }
mv "$partial" "$target"
echo "backup written: $target ($(du -h "$target" | cut -f1))"

ls -1t "$BACKUP_DIR"/terrific_bites-*.dump | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f -- "$old"
done
