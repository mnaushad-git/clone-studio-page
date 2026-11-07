#!/usr/bin/env bash
# Replaces the Terrific Bites database with a backup. DESTRUCTIVE: orders placed after the
# backup was taken are lost, so a fresh safety backup is taken first.
#
#   deploy/scripts/restore-db.sh <path-to.dump>
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DUMP="${1:?usage: restore-db.sh <path-to.dump>}"
[[ -f "$DUMP" ]] || { echo "no such file: $DUMP" >&2; exit 2; }

compose() { docker compose --env-file "$DEPLOY_DIR/.env.prod" -f "$DEPLOY_DIR/docker-compose.prod.yml" "$@"; }

compose exec -T postgres pg_restore --list < "$DUMP" > /dev/null || { echo "unreadable dump" >&2; exit 2; }

read -r -p "This replaces the terrific_bites database with $(basename "$DUMP"). Type RESTORE to continue: " answer
[[ "$answer" == "RESTORE" ]] || { echo "cancelled"; exit 1; }

"$DEPLOY_DIR/scripts/backup-db.sh" pre-restore

compose stop api celery-worker celery-beat
compose exec -T postgres pg_restore -U terrific_bites -d terrific_bites --clean --if-exists --no-owner --single-transaction < "$DUMP"
compose up -d --no-build api celery-worker celery-beat
echo "restore finished; run deploy/scripts/smoke.sh"
