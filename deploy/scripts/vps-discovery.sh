#!/usr/bin/env bash
# Read-only inventory of the VPS for the Terrific Bites readiness report. It changes
# nothing, restarts nothing, and deliberately never reads .env files, container
# environment variables or Caddy config values other than site names.
#
#   ssh <user>@187.127.159.23 'bash -s' < deploy/scripts/vps-discovery.sh > vps-report.txt
set -u
PROPOSED_PORT="${PROPOSED_PORT:-18010}"
section() { printf '\n=== %s ===\n' "$1"; }
SUDO=""
sudo -n true 2>/dev/null && SUDO="sudo -n"

section "identity"
echo "user: $(whoami)  host: $(hostname)  passwordless sudo: ${SUDO:-no}"
grep -E '^(PRETTY_NAME)=' /etc/os-release; uname -r; uptime

section "capacity"
echo "cpus: $(nproc)"; free -h; df -h -x tmpfs -x devtmpfs -x overlay 2>/dev/null
swapon --show 2>/dev/null

section "listening ports"
$SUDO ss -ltnp 2>/dev/null | awk 'NR==1 || !/127\.0\.0\.53/' | cut -c1-120

section "proposed port ${PROPOSED_PORT}"
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${PROPOSED_PORT}$"; then
  echo "IN USE"
else
  echo "free"
fi

section "firewall"
$SUDO ufw status 2>/dev/null | head -20

section "docker"
if command -v docker >/dev/null; then
  $SUDO docker version --format 'engine {{.Server.Version}}' 2>&1 | head -1
  $SUDO docker compose version 2>&1 | head -1
  $SUDO docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | cut -c1-170
  echo "-- compose projects"; $SUDO docker compose ls -a 2>/dev/null | cut -c1-120
  echo "-- networks"; $SUDO docker network ls --format '{{.Name}} {{.Driver}}'
  echo "-- volumes"; $SUDO docker volume ls --format '{{.Name}}'
  echo "-- memory"; $SUDO docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' 2>/dev/null
  echo "-- disk"; $SUDO docker system df 2>/dev/null
else
  echo "docker not installed"
fi

section "reverse proxy and TLS"
for s in caddy nginx apache2 traefik; do
  printf '%s: installed=%s active=%s\n' "$s" \
    "$(command -v "$s" >/dev/null && echo yes || echo no)" \
    "$(systemctl is-active "$s" 2>/dev/null)"
done
echo "-- Caddy sites (names only)"
$SUDO sh -c 'cat /etc/caddy/Caddyfile /etc/caddy/conf.d/* /etc/caddy/sites/* 2>/dev/null' \
  | grep -E '^[[:space:]]*[a-zA-Z0-9*.:-]+(,[[:space:]]*[a-zA-Z0-9*.:-]+)*[[:space:]]*\{' | cut -c1-100
echo "-- Caddy import lines"; $SUDO grep -hE '^[[:space:]]*import ' /etc/caddy/Caddyfile 2>/dev/null
echo "-- Caddy upstreams (host:port only)"
$SUDO sh -c 'cat /etc/caddy/Caddyfile /etc/caddy/conf.d/* /etc/caddy/sites/* 2>/dev/null' \
  | grep -E '^[[:space:]]*reverse_proxy' | awk '{print $2}' | sort -u
echo "-- Caddy container"
command -v docker >/dev/null && $SUDO docker ps --format '{{.Names}} {{.Image}}' | grep -iE 'caddy|nginx|traefik'

section "postgresql"
systemctl is-active postgresql 2>/dev/null
command -v psql >/dev/null && psql --version
command -v docker >/dev/null && $SUDO docker ps --format '{{.Names}} {{.Image}}' | grep -iE 'postgres|timescale|postgis'

section "redis"
systemctl is-active redis-server redis 2>/dev/null | head -2
command -v docker >/dev/null && $SUDO docker ps --format '{{.Names}} {{.Image}}' | grep -i redis

section "applications and backups"
ls -la /opt /srv /var/www 2>/dev/null | cut -c1-90
$SUDO crontab -l 2>/dev/null | cut -d' ' -f1-6 | cut -c1-90
ls /etc/cron.d 2>/dev/null
systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null \
  | awk '{print $1}' | grep -vE '^(systemd-|dbus|getty|serial-|ssh|cron|rsyslog|polkit|networkd|unattended|user@|multipath|packagekit|snapd|qemu|ModemManager|fwupd)' | head -30
