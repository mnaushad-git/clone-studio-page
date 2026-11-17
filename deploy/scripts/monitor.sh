#!/usr/bin/env bash
# Checks the Terrific Bites stack and sends an alert when its state changes, so a lasting
# failure alerts once and recovery alerts once. Read-only towards the application, and it
# only looks at this Compose project, never other applications on the server.
#
# Cron: */5 * * * * /opt/terrific-bites/deploy/scripts/monitor.sh >> /var/log/terrific-bites-monitor.log 2>&1
#
# Sends to each channel configured in .env.prod: ALERT_WEBHOOK_URL and/or email
# (ALERT_EMAIL_TO, ALERT_EMAIL_FROM, ALERT_SMTP_URL, ALERT_SMTP_USER, ALERT_SMTP_PASSWORD).
# Send a test message through them with: monitor.sh --test-alert
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

# Curl reads the login from stdin, so the password never appears in the process list.
send_email() {
  local subject="$1" body="$2" to from smtp_url user password message code tls=(--ssl-reqd)
  to="$(env_value ALERT_EMAIL_TO)"; from="$(env_value ALERT_EMAIL_FROM)"
  smtp_url="$(env_value ALERT_SMTP_URL)"; user="$(env_value ALERT_SMTP_USER)"
  password="$(env_value ALERT_SMTP_PASSWORD)"
  if [[ -z "$from" || -z "$smtp_url" || -z "$user" || -z "$password" ]]; then
    echo "email alert settings are incomplete" >&2
    return 1
  fi
  # Plain SMTP is only ever acceptable on loopback, which is how this is tested.
  [[ "$smtp_url" == smtp://127.0.0.1:* ]] && tls=()
  password="${password//\\/\\\\}"; password="${password//\"/\\\"}"
  message="$(mktemp)"
  {
    printf 'From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n' \
      "$from" "$to" "${subject//[$'\r\n']/ }" "$(date -R)"
    printf '%s\r\n' "${body//[$'\r\n']/ }"
  } >"$message"
  printf 'user = "%s:%s"\n' "$user" "$password" | curl -s -m 30 "${tls[@]}" --config - \
    --url "$smtp_url" --mail-from "$from" --mail-rcpt "$to" --upload-file "$message"
  code=$?
  rm -f "$message"
  return "$code"
}

send_webhook() {
  local payload
  payload="$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
  curl -s -m 15 -o /dev/null -f -H 'Content-Type: application/json' \
    -d "{\"text\":\"$payload\",\"content\":\"$payload\"}" "$1"
}

# Returns non-zero if any configured channel failed. Prints what happened to each one.
send_alert() {
  local subject="$1" message="$2" stamp webhook email status=0 sent=0
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  webhook="$(env_value ALERT_WEBHOOK_URL)"
  email="$(env_value ALERT_EMAIL_TO)"
  if [[ -n "$webhook" ]]; then
    if send_webhook "$webhook" "$message"; then
      echo "$stamp webhook accepted the alert"; sent=1
    else
      echo "$stamp webhook alert could not be sent" >&2; status=1
    fi
  fi
  if [[ -n "$email" ]]; then
    if send_email "$subject" "$message"; then
      echo "$stamp mail server accepted the alert for $email"; sent=1
    else
      echo "$stamp email alert could not be sent" >&2; status=1
    fi
  fi
  if [[ "$sent" == 0 && "$status" == 0 ]]; then
    echo "$stamp no alert channel is configured, so this alert was not sent: $message" >&2
  fi
  return "$status"
}

if [[ "${1:-}" == "--test-alert" ]]; then
  send_alert "Terrific Bites test alert" "Test alert from monitor.sh on $(hostname). No action needed."
  code=$?
  echo "A server accepting a message doesn't prove delivery: confirm it arrived." >&2
  exit "$code"
fi

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
    subject="Terrific Bites recovered"
    message="Terrific Bites recovered at $stamp"
  else
    subject="Terrific Bites problem"
    message="Terrific Bites problem at $stamp: $current"
  fi
  # On failure the old state stays, so the next run tries to send this alert again.
  send_alert "$subject" "$message" || exit 1
  printf '%s' "$current" >"$STATE_FILE"
fi

[[ "$current" == "ok" ]]
