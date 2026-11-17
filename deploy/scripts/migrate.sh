#!/usr/bin/env bash
# Repeatable production migration: back up, show what will change, apply, verify.
# Alembic is idempotent at head, so re-running is safe. Uses the TB_IMAGE_TAG in .env.prod.
#
#   deploy/scripts/migrate.sh
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
compose() { docker compose --env-file "$DEPLOY_DIR/.env.prod" -f "$DEPLOY_DIR/docker-compose.prod.yml" "$@"; }

compose up -d --wait postgres redis
"$DEPLOY_DIR/scripts/backup-db.sh" pre-migrate

echo "--- before"; compose run --rm migrate alembic current
compose run --rm migrate alembic upgrade head
echo "--- after";  compose run --rm migrate alembic current

head_rev="$(compose run --rm -T migrate alembic heads | awk '{print $1}')"
current_rev="$(compose run --rm -T migrate alembic current | awk '{print $1}' | tail -n 1)"
[[ -n "$head_rev" && "$head_rev" == "$current_rev" ]] || {
  echo "database is at '$current_rev', expected '$head_rev'" >&2
  exit 1
}
echo "migrated to $current_rev"
