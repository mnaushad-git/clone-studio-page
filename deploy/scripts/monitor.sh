#!/usr/bin/env bash
# Checks the Terrific Bites stack and sends an alert when its state changes, so a lasting
# failure alerts once and recovery alerts once. Read-only towards the application, and it
# only looks at this Compose project, never other applications on the server.
#
# Cron: */5 * * * * /opt/terrific-bites/deploy/scripts/monitor.sh >> /var/log/terrific-bites-monitor.log 2>&1
#
# This runs on the VPS, so it can't report the VPS itself going down. An external uptime
# check on /api/v1/health is needed as well: see the runbook.
set -uo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$DEPLOY_DIR/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-$DEPLOY_DIR/docker-compose.prod.yml}"
STATE_FILE="${MONITOR_STATE_FILE:-$DEPLOY_DIR/.monitor-state}"
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"
HEALTH_URL="${HEALTH_URL:-https://api.terrific-bites.trunexus.ai/api/v1/health}"
DISK_LIMIT_PERCENT="${DISK_LIMIT_PERCENT:-85}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"
SERVICES=(postgres redis api celery-worker celery-beat)

# Reads one value by name, without sourcing a file that holds secrets.
env_value() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n 1 | cut -d= -f2-; }
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

failures=()

for service in "${SERVICES[@]}"; do
  id="$(compose ps -q "$service" 2>/dev/null | head -n 1)"
  if [[ -z "$id" ]]; then
    failures+=("$service: not running")
    continue
  fi
  state="$(docker inspect --format '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null)"
  case "$state" in
    running/healthy | running/none | running/starting) ;;
    *) failures+=("$service: $state") ;;
  esac
done

code="$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$HEALTH_URL")"
[[ "$code" == "200" ]] || failures+=("public health check: HTTP $code")

# The application's own view: worker heartbeat, order queue, failed events.
if report="$(compose exec -T api python -m app.scripts.ops_health_check 2>/dev/null)"; then
  :
else
  failing="$(printf '%s' "$report" | grep -oE '"name": "[a-z_]+", "ok": false, "detail": "[^"]*"' \
    | sed -E 's/"name": "([a-z_]+)", "ok": false, "detail": "([^"]*)"/\1: \2/')"
  if [[ -n "$failing" ]]; then
    while IFS= read -r line; do failures+=("$line"); done <<<"$failing"
  else
    failures+=("application health check could not run")
  fi
fi

disk="$(df --output=pcent "$DEPLOY_DIR" 2>/dev/null | tail -n 1 | tr -dc '0-9')"
if [[ -n "$disk" && "$disk" -ge "$DISK_LIMIT_PERCENT" ]]; then
  failures+=("disk ${disk}% full, limit ${DISK_LIMIT_PERCENT}%")
fi

newest="$(ls -1t "$BACKUP_DIR"/terrific_bites-*.dump 2>/dev/null | head -n 1)"
if [[ -z "$newest" ]]; then
  failures+=("no database backup found")
else
  age_hours=$((($(date +%s) - $(date -r "$newest" +%s)) / 3600))
  if [[ "$age_hours" -ge "$BACKUP_MAX_AGE_HOURS" ]]; then
    failures+=("newest backup is ${age_hours}h old, limit ${BACKUP_MAX_AGE_HOURS}h")
  fi
fi

if ((${#failures[@]})); then
  current="$(printf '%s; ' "${failures[@]}")"
  current="${current%; }"
else
  current="ok"
fi
previous="$(cat "$STATE_FILE" 2>/dev/null || echo ok)"
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "$stamp $current"

if [[ "$current" != "$previous" ]]; then
  if [[ "$current" == "ok" ]]; then
    message="Terrific Bites recovered at $stamp"
  else
    message="Terrific Bites problem at $stamp: $current"
  fi
  webhook="$(env_value ALERT_WEBHOOK_URL)"
  if [[ -n "$webhook" ]]; then
    payload="$(printf '%s' "$message" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
    if ! curl -s -m 15 -o /dev/null -f -H 'Content-Type: application/json' \
      -d "{\"text\":\"$payload\",\"content\":\"$payload\"}" "$webhook"; then
      # Keep the old state, so the next run tries to send this alert again.
      echo "$stamp alert could not be sent" >&2
      exit 1
    fi
  else
    echo "$stamp ALERT_WEBHOOK_URL is not set, so this alert was not sent: $message" >&2
  fi
  printf '%s' "$current" >"$STATE_FILE"
fi

[[ "$current" == "ok" ]]
