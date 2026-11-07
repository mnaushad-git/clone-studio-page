# VPS access and discovery

For the person with access to the Hostinger VPS (`187.127.159.23`). Every command here only
reads. Nothing restarts, changes or interrupts myMakan, Maskan or any other service.

The key `maskan_hostinger` has **not** been tested against this server, so don't assume it
works. Its comment is `claude-code-deploy@maskan`, and it may belong to another deployment.

## What's needed for access

| Requirement | Detail |
|---|---|
| SSH username | Not known. Find it in hPanel: VPS → Overview → SSH access |
| SSH key | Either confirm `maskan_hostinger` is meant for this work, or preferably add a new key used only for Terrific Bites |
| Permissions for discovery | Read access. Passwordless `sudo` gives a fuller report; without it, some sections come back empty |
| Permissions for deployment | Membership of the `docker` group, write access to `/opt/terrific-bites`, and permission to add a Caddy site and reload Caddy |
| DNS | Access to trunexus.ai in hPanel, to add `A` records once approved |

To add a dedicated key, run this on your computer and add the `.pub` file's contents through
hPanel or to `~/.ssh/authorized_keys` on the server:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/terrific_bites_vps -C "terrific-bites-deploy"
```

## Step 1: verify access

Replace `<user>` with the username, and use a different key path if you created a new key.

```bash
# Is the server's identity the one already recorded on this machine?
ssh-keygen -F 187.127.159.23 | head -3
ssh-keyscan -T 10 -t ed25519 187.127.159.23 2>/dev/null | ssh-keygen -lf -

# Does the key work? BatchMode makes it fail instead of prompting for a password.
ssh -i ~/.ssh/maskan_hostinger -o IdentitiesOnly=yes -o BatchMode=yes \
    -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
    <user>@187.127.159.23 'echo "OK: $(whoami)@$(hostname), groups: $(id -nG)"'
```

| Result | Meaning | Next step |
|---|---|---|
| `OK: ...` | The key is authorized for that user | Go to step 2 |
| `Permission denied (publickey)` | The key isn't authorized for that user | Check the username, or add a dedicated key. **Stop** if neither is possible |
| `Host key verification failed` | The server's identity doesn't match this machine's record | **Stop.** Confirm the fingerprint in hPanel before going further |
| `Connection timed out` | Port 22 is blocked or SSH uses another port | Check the firewall and SSH port in hPanel |

## Step 2: run the discovery report

```bash
ssh -i ~/.ssh/maskan_hostinger -o IdentitiesOnly=yes -o BatchMode=yes <user>@187.127.159.23 \
    'bash -s' < deploy/scripts/vps-discovery.sh > vps-report.txt
```

The script doesn't read `.env` files, container environment variables, or anything from the
Caddy configuration other than site names and upstream addresses. Still skim `vps-report.txt`
before sharing it, because it lists the applications and domains on the server.

It records a baseline of what's running and how each site responds. Keep that file: the
regression check after every staging step compares against it.

## Step 3: individual checks

For running parts of the report separately. All are read-only.

| Question | Command |
|---|---|
| CPU, RAM, disk | `nproc; free -h; df -h -x tmpfs -x devtmpfs` |
| Free ports | `ss -ltn` (18010 and 18011 should not be listed) |
| Docker and Compose | `docker version --format '{{.Server.Version}}'; docker compose version` |
| Containers | `docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'` |
| Compose projects | `docker compose ls -a` |
| Container memory use | `docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'` |
| Caddy on the host? | `systemctl is-active caddy; command -v caddy` |
| Caddy in a container? | `docker ps --format '{{.Names}} {{.Image}}' \| grep -i caddy` |
| PostgreSQL on the host? | `systemctl is-active postgresql` |
| PostgreSQL containers | `docker ps --format '{{.Names}} {{.Image}}' \| grep -iE 'postgres\|postgis'` |
| Firewall | `sudo -n ufw status` |

DNS can be checked from anywhere:

```bash
nslookup api.terrific-bites.trunexus.ai 8.8.8.8   # should not exist until the record is added
nslookup -type=NS trunexus.ai 8.8.8.8             # dns-parking.com means hPanel manages it
```

## What the report has to show before staging

| Check | Needed |
|---|---|
| Free memory | About 2.5 GB. The stack's limits add up to about 2.2 GB, and staging needs the same again, plus 512 MB for its frontend, if it runs alongside production |
| Free disk | At least 10 GB for images, database and 14 days of backups |
| Ports | 18010 and 18011 free on loopback |
| Docker | Engine and Compose v2 available to the deploy user |
| Caddy | Known whether it's on the host or in a container, and where its config lives |
| Baseline | Every existing site and container recorded as healthy, so later differences are meaningful |
