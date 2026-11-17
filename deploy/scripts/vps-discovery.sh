#!/usr/bin/env bash
# Read-only inventory of the VPS for the Terrific Bites deployment report.
#
# It installs, deletes, restarts, stops and reconfigures nothing. The only thing it creates is
# one report file, readable by its owner only, and it refuses to overwrite an existing one.
# It never reads .env files or container environment variables. From Caddy config it reports
# only site names, upstream addresses and import paths; other lines never reach the report.
# Cron is reported as schedules only, because a cron command line can hold a password.
#
# On the VPS: see docs/deployment/vps-access-and-discovery.md
#   bash vps-discovery.sh             writes /tmp/tb-vps-report.txt
#   bash vps-discovery.sh --stdout    prints the report and creates no file
#
# Keep this file ASCII: Run-VpsDiscovery.ps1 and Copy-VpsDiscovery.ps1 both depend on it.
set -u
umask 077

REPORT="${TB_VPS_REPORT:-/tmp/tb-vps-report.txt}"
PROPOSED_PORTS="${PROPOSED_PORTS:-18010 18011 18020 18069 18072}"
NEED_MEMORY_MB="${NEED_MEMORY_MB:-4500}"
NEED_DISK_GB="${NEED_DISK_GB:-25}"
APPS='makan|maskan'

SUDO=""
if [ "$(id -u)" -ne 0 ] && sudo -n true 2>/dev/null; then SUDO="sudo -n"; fi
HAS_DOCKER=""
command -v docker >/dev/null 2>&1 && HAS_DOCKER=yes

section() { printf '\n=== %s ===\n' "$1"; }
d() { [ -n "$HAS_DOCKER" ] && $SUDO docker "$@"; }

# Last line of defence over the whole report: masks credential-shaped values if one ever
# appears in a name or path.
redact() {
  sed -E \
    -e 's/([A-Za-z0-9_-]*(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_KEY)[A-Za-z0-9_-]*=)[^[:space:]]*/\1<redacted>/Ig' \
    -e 's#(://)[^/:@[:space:]]+:[^/@[:space:]]+@#\1<redacted>@#g'
}

caddy_containers() { d ps --format '{{.Names}} {{.Image}}' | awk 'tolower($0) ~ /caddy/ {print $1}'; }

# Raw config. Only ever piped into the filters below; never print this directly.
caddy_raw() {
  $SUDO sh -c 'cat /etc/caddy/Caddyfile /etc/caddy/conf.d/* /etc/caddy/sites/* 2>/dev/null'
  for c in $(caddy_containers); do
    for src in $(d inspect -f '{{range .Mounts}}{{println .Source .Destination}}{{end}}' "$c" \
      | awk '$2 ~ /^\/etc\/caddy/ {print $1}'); do
      $SUDO find "$src" -maxdepth 2 -type f -size -1024k -exec cat {} + 2>/dev/null
    done
  done
}
# A site block starts in column 0 and ends with "{". Snippets, matchers and comments do not count.
caddy_sites() { grep -E '^[^#[:space:](@{][^{]*\{[[:space:]]*$' | tr -d '{' | cut -c1-200 | sort -u; }
caddy_upstreams() {
  grep -E '^[[:space:]]*reverse_proxy[[:space:]]' \
    | awk '{for (i = 2; i <= NF; i++) { if ($i == "{") break; if ($i !~ /^@/) print $i }}' \
    | sort -u | cut -c1-100
}
caddy_imports() { grep -E '^[[:space:]]*import[[:space:]]' | awk '{print $2}' | sort -u | cut -c1-120; }
schedule_only() { awk '/^[0-9*@]/ { if ($1 ~ /^@/) print $1; else print $1, $2, $3, $4, $5 }'; }

collect() {
  CADDY_SITES="$(caddy_raw | caddy_sites)"
  CADDY_UPSTREAMS="$(caddy_raw | caddy_upstreams)"

  section "identity"
  echo "user: $(whoami)  host: $(hostname)  via sudo: ${SUDO:-no}"
  date -u; grep -E '^PRETTY_NAME=' /etc/os-release; uname -r; uptime
  echo "tb-deploy account: $(id tb-deploy 2>&1)"
  echo "docker group: $(getent group docker | cut -d: -f1,4)"

  section "cpu"
  echo "cpus: $(nproc)"; grep -m1 'model name' /proc/cpuinfo
  top -bn1 | sed -n '1,5p'
  echo "-- vmstat, five one-second samples"; vmstat 1 5

  section "memory and swap"
  free -h; swapon --show
  sysctl vm.swappiness vm.overcommit_memory
  echo "out-of-memory events, last 30 days: $(journalctl -k --since '30 days ago' --no-pager 2>/dev/null | grep -ciE 'out of memory|oom-kill')"
  echo "-- largest processes (name only)"
  ps -eo rss=,pcpu=,comm= --sort=-rss | head -15 | awk '{printf "%6d MB %5s%% %s\n", $1 / 1024, $2, $3}'

  section "disk"
  df -h -x tmpfs -x devtmpfs -x overlay
  echo "-- inodes on /"; df -i / | tail -1
  echo "-- application and backup directory sizes"
  timeout 60 nice -n 19 du -sh /opt/* /srv/* /var/www/* /var/backups 2>/dev/null | sort -h | tail -20

  section "listening ports"
  echo "-- tcp"; $SUDO ss -ltnp | awk 'NR==1 || !/127\.0\.0\.53/' | cut -c1-160
  echo "-- udp"; $SUDO ss -lunp | awk 'NR==1 || !/127\.0\.0\.53/' | cut -c1-160
  echo "-- ports proposed for Terrific Bites"
  for port in $PROPOSED_PORTS; do
    if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"; then echo "$port IN USE"; else echo "$port free"; fi
  done
  echo "-- well-known ports in use (web, PostgreSQL, Redis, Odoo, Caddy admin)"
  ss -ltn | awk '{print $4}' | grep -E '[:.](80|443|2019|5432|6379|8069|8072)$'

  section "firewall"
  $SUDO ufw status verbose 2>&1 | head -40
  echo "-- iptables INPUT"; $SUDO iptables -S INPUT 2>&1 | head -30
  echo "-- iptables DOCKER-USER"; $SUDO iptables -S DOCKER-USER 2>&1 | head -20
  echo "-- the Hostinger firewall is not visible from here: check it in hPanel"

  section "network"
  ip -br addr | cut -c1-120
  echo "-- public DNS as seen from this VPS"
  for host in terrific-bites.trunexus.ai api.terrific-bites.trunexus.ai; do
    echo "$host: $(getent hosts "$host" | awk '{print $1}' | tr '\n' ' ')"
  done
  curl -s -m 10 -o /dev/null -w 'docker hub registry: HTTP %{http_code}\n' https://registry-1.docker.io/v2/

  section "docker"
  if [ -n "$HAS_DOCKER" ]; then
    d version --format 'engine {{.Server.Version}}' 2>&1 | head -1
    d compose version 2>&1 | head -1
    d info --format 'root={{.DockerRootDir}} storage={{.Driver}} log={{.LoggingDriver}} cgroup={{.CgroupVersion}}'
    echo "-- daemon log rotation"; $SUDO grep -E 'max-size|max-file' /etc/docker/daemon.json 2>/dev/null | cut -c1-80
    echo "-- containers"; d ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | cut -c1-190
    echo "-- compose projects"; d compose ls -a | cut -c1-200
    ids="$(d ps -aq)"
    if [ -n "$ids" ]; then
      echo "-- memory limits (0 means none), restart policy, compose directory"
      d inspect -f '{{.Name}} mem={{.HostConfig.Memory}} restart={{.HostConfig.RestartPolicy.Name}} dir={{index .Config.Labels "com.docker.compose.project.working_dir"}}' $ids | cut -c1-170
      echo "-- container networks"; d ps --format '{{.Names}} {{.Networks}}' | cut -c1-120
    fi
    echo "-- live usage"; d stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}'
    echo "-- networks and subnets"
    d network inspect -f '{{.Name}} {{.Driver}} {{range .IPAM.Config}}{{.Subnet}} {{end}}' $(d network ls -q) | cut -c1-100
    echo "-- images"; d images --format '{{.Repository}}:{{.Tag}} {{.Size}} {{.CreatedSince}}' | head -40
    echo "-- disk summary"; d system df
    echo "-- volumes and sizes"; timeout 90 $SUDO docker system df -v | awk '/^Local Volumes/,/^Build cache/' | cut -c1-100
  else
    echo "docker not installed"
  fi

  section "reverse proxy and TLS"
  for s in caddy nginx apache2 traefik; do
    printf '%s: installed=%s active=%s\n' "$s" \
      "$(command -v "$s" >/dev/null 2>&1 && echo yes || echo no)" "$(systemctl is-active "$s" 2>/dev/null)"
  done
  command -v caddy >/dev/null 2>&1 && caddy version 2>/dev/null | cut -c1-40
  systemctl show caddy -p LoadState,ActiveState,FragmentPath 2>/dev/null
  echo "-- what owns 80, 443 and the Caddy admin port"
  $SUDO ss -ltnp '( sport = :80 or sport = :443 or sport = :2019 )' | cut -c1-160
  echo "-- proxy containers"; d ps --format '{{.Names}} {{.Image}} {{.Ports}}' | grep -iE 'caddy|nginx|traefik' | cut -c1-170
  for c in $(caddy_containers); do
    echo "-- container $c"
    d inspect -f 'mode={{.HostConfig.NetworkMode}} networks={{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}dir={{index .Config.Labels "com.docker.compose.project.working_dir"}}' "$c" | cut -c1-200
    d inspect -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}; {{end}}' "$c" | cut -c1-400
  done
  echo "-- Caddy sites (names only)"; printf '%s\n' "$CADDY_SITES"
  echo "-- Caddy upstreams (addresses only)"; printf '%s\n' "$CADDY_UPSTREAMS"
  echo "-- Caddy import paths"; caddy_raw | caddy_imports

  section "postgresql, redis and odoo"
  echo "host services: postgresql=$(systemctl is-active postgresql 2>/dev/null) redis-server=$(systemctl is-active redis-server 2>/dev/null) odoo=$(systemctl is-active odoo 2>/dev/null)"
  command -v psql >/dev/null 2>&1 && psql --version
  command -v odoo >/dev/null 2>&1 && echo "odoo binary: $(command -v odoo)"
  echo "-- containers"; d ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}' | grep -iE 'postgres|timescale|postgis|redis|valkey|odoo' | cut -c1-170
  echo "-- volumes"; d volume ls --format '{{.Name}}' | grep -iE 'postgres|pg|redis|odoo'
  echo "-- directories"; ls -d /opt/*odoo* /srv/*odoo* /var/lib/odoo /etc/odoo 2>/dev/null
  echo "-- Caddy sites mentioning odoo"; printf '%s\n' "$CADDY_SITES" | grep -i odoo

  section "applications from the old shared VPS (myMakan, Maskan): none expected here"
  echo "-- containers"; d ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}' | grep -iE "$APPS" | cut -c1-170
  echo "-- live usage"; d stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}' | grep -iE "$APPS"
  echo "-- volumes"; d volume ls --format '{{.Name}}' | grep -iE "$APPS"
  echo "-- networks"; d network ls --format '{{.Name}}' | grep -iE "$APPS"
  echo "-- images"; d images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -iE "$APPS"
  echo "-- directories"; ls -d /opt/* /srv/* /var/www/* 2>/dev/null | grep -iE "$APPS"
  echo "-- Caddy sites"; printf '%s\n' "$CADDY_SITES" | grep -iE "$APPS"
  echo "-- host services"
  systemctl list-units --type=service --all --no-pager --no-legend 2>/dev/null | awk '{print $1, $3, $4}' | grep -iE "$APPS"

  section "other applications and scheduled jobs"
  ls -la /opt /srv /var/www 2>/dev/null | cut -c1-90
  echo "-- compose files and Caddyfiles (paths only)"
  find /opt /srv /var/www /root /home -maxdepth 4 -type f \( -name 'docker-compose*.y*ml' -o -name 'compose*.y*ml' -o -name 'Caddyfile' \) -not -path '*/node_modules/*' 2>/dev/null | cut -c1-140
  echo "-- running host services"
  systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null \
    | awk '{print $1}' | grep -vE '^(systemd-|dbus|getty|serial-|ssh|cron|rsyslog|polkit|networkd|unattended|user@|multipath|packagekit|snapd|qemu|ModemManager|fwupd)' | head -30
  echo "-- root crontab (schedules only)"; $SUDO crontab -l 2>/dev/null | schedule_only
  echo "-- /etc/cron.d (file names only)"; ls /etc/cron.d 2>/dev/null

  section "terrific bites (anything already deployed)"
  d ps -a --format '{{.Names}} {{.Status}}' | grep -i terrific
  d volume ls --format '{{.Name}}' | grep -i terrific
  ls -ld /opt/terrific-bites* 2>/dev/null

  section "backup and rollback readiness"
  for tool in restic borg rclone pg_dump pg_dumpall rsync age; do
    printf '%s: %s\n' "$tool" "$(command -v "$tool" >/dev/null 2>&1 && echo installed || echo absent)"
  done
  echo "-- scheduled jobs that look like backups (schedules only)"
  { $SUDO crontab -l 2>/dev/null; $SUDO sh -c 'cat /etc/crontab /etc/cron.d/* 2>/dev/null'; } \
    | grep -iE 'backup|pg_dump|restic|borg|rclone|snapshot' | schedule_only
  systemctl list-timers --all --no-pager --no-legend 2>/dev/null | grep -iE 'backup|snapshot|restic|borg' | cut -c1-120
  echo "-- backup locations"; ls -ld /var/backups /backup /backups /opt/backups 2>/dev/null
  echo "-- provider snapshots are not visible from here: check hPanel, VPS, Snapshots & Backups"

  section "baseline: existing sites (HTTP status)"
  printf '%s\n' "$CADDY_SITES" | tr ', ' '\n\n' | sed -E 's#^https?://##; s#[:/].*$##' \
    | grep -E '^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' | sort -u | head -40 | while read -r site; do
        printf '%s %s\n' "$site" "$(curl -s -m 10 -o /dev/null -w '%{http_code}' "https://$site")"
      done

  section "baseline: containers"
  d ps --format '{{.Names}} {{.Status}}' | sort

  section "capacity floor (not a verdict: existing apps' peak usage still has to be allowed for)"
  available_mb=$(free -m | awk '/^Mem:/ {print $7}')
  disk_gb=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
  if [ "${available_mb:-0}" -ge "$NEED_MEMORY_MB" ]; then memory_result=OK; else memory_result=INSUFFICIENT; fi
  if [ "${disk_gb:-0}" -ge "$NEED_DISK_GB" ]; then disk_result=OK; else disk_result=INSUFFICIENT; fi
  echo "memory: ${available_mb} MB available, ${NEED_MEMORY_MB} MB floor: ${memory_result}"
  echo "disk: ${disk_gb} GB free on /, ${NEED_DISK_GB} GB floor: ${disk_result}"
}

if [ "${1:-}" = "--stdout" ]; then
  collect </dev/null 2>&1 | redact
  exit 0
fi

if [ -e "$REPORT" ] || [ -L "$REPORT" ]; then
  echo "A report already exists at $REPORT, and this script never overwrites one."
  echo "Delete it, then run this again:  rm -f $REPORT"
  exit 1
fi
# noclobber makes the shell create the file exclusively, so a planted symlink cannot be followed.
if ! ( set -C; : >"$REPORT" ) 2>/dev/null; then
  echo "Could not create $REPORT"
  exit 1
fi

echo "Collecting read-only information. This usually takes 1 to 3 minutes..."
collect </dev/null 2>&1 | redact >>"$REPORT"

echo
echo "Report saved, readable by this account only: $REPORT ($(wc -l <"$REPORT") lines)"
echo "Display it:  cat $REPORT"
echo "Delete it:   rm -f $REPORT"
