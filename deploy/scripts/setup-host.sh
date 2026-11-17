#!/usr/bin/env bash
# One-time host setup for the dedicated staging VPS, run as root:
#   sudo bash /home/deploy/apps/terrific-bites/deploy/scripts/setup-host.sh
#
# 1. Firewall: allows SSH (22), HTTP and HTTPS, then enables ufw. SSH is allowed before
#    enabling, and existing sessions stay connected. Nothing else is opened: every
#    container port is bound to 127.0.0.1 only.
# 2. Caddy from its official apt repository, with /etc/caddy/Caddyfile importing
#    /etc/caddy/sites/*.caddy, and the staging API and temporary preview sites installed.
#    The storefront site (terrific-bites.caddy) is NOT installed: that is the cutover.
#
# Safe to re-run. Changes no DNS, no SSH settings and no container.
set -euo pipefail

[[ "$(id -u)" == 0 ]] || { echo "run as root: sudo bash $0" >&2; exit 1; }
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SITES=(api.terrific-bites.caddy preview.terrific-bites.caddy)

echo "== firewall"
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP (Caddy, ACME)'
ufw allow 443/tcp comment 'HTTPS (Caddy)'
ufw --force enable
ufw status verbose

echo "== caddy package"
if ! command -v caddy > /dev/null; then
  apt-get update -q
  apt-get install -y -q debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -q
  apt-get install -y -q caddy
fi
caddy version

echo "== caddy configuration"
mkdir -p /etc/caddy/sites
[[ -f /etc/caddy/Caddyfile.default ]] || cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.default
printf '# Each site is a file in /etc/caddy/sites. See deploy/caddy/ in the repository.\nimport /etc/caddy/sites/*.caddy\n' \
  > /etc/caddy/Caddyfile
for site in "${SITES[@]}"; do
  install -m 644 "$REPO/deploy/caddy/$site" "/etc/caddy/sites/$site"
done
ls -l /etc/caddy/sites
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl enable --now caddy
systemctl reload caddy
systemctl is-active caddy

echo "== listening"
ss -ltn | awk 'NR > 1 {print $4}' | sort -u | tr '\n' ' '
echo
echo "done. Certificates are issued once each hostname's DNS points at this VPS."
