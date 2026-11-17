# VPS access and discovery

For the person with access to the dedicated Hostinger KVM 4 VPS (`2.25.11.35`, Ubuntu 24.04),
which hosts only Terrific Bites client staging. Discovery only reads and changes nothing.

## Recommended: run discovery from the hPanel browser terminal

This needs no new account and no change to the server, and it sees Docker because the browser
terminal is already logged in as root.

1. On your computer, from the repository folder, copy the one-line command to the clipboard:
   `powershell -ExecutionPolicy Bypass -File deploy\scripts\Copy-VpsDiscovery.ps1`
2. In hPanel open **VPS**, select `2.25.11.35`, **Manage**, then **Browser terminal**.
3. Paste the command and press Enter. It takes 1 to 3 minutes. A `sha256sum` error means the paste
   was damaged and nothing ran, so paste it again.
4. Run `cat /tmp/tb-vps-report.txt` and copy the output into a local `vps-report.txt` (git-ignored).
5. Run `rm -f /tmp/tb-vps-report.txt`. The report is the only file left behind, and only its owner
   can read it. The script won't overwrite an earlier report, so delete it before running again.

Parts 1 to 4 below are the alternative: a dedicated SSH user. **Creating that user is a change to
the server and needs authorization first.** It doesn't affect running applications, and part 7
shows how to undo it.

## 1. Find the VPS username (hPanel)

1. Log in to [hPanel](https://hpanel.hostinger.com) and open **VPS**.
2. Select the server with IP `2.25.11.35` and click **Manage**.
3. On the **Overview** page, the details card lists the SSH username (normally `root`) and the
   IP address.

Hostinger's menu labels vary by plan and over time, so yours may differ slightly.

## 2. Install the dedicated key (hPanel browser terminal)

The dedicated key is `~/.ssh/terrific_bites_vps`. Its public half is safe to paste; never share
the file without `.pub`. Show it in PowerShell:

```powershell
Get-Content "$env:USERPROFILE\.ssh\terrific_bites_vps.pub"
```

Don't use hPanel's **SSH keys** page for this, because a key added there logs in as root. Use a
dedicated user instead:

1. On the VPS **Overview** page, open **Browser terminal**. It opens logged in as root.
2. Paste these, replacing `PASTE_PUBLIC_KEY_HERE` with the line you just displayed:

```bash
adduser --disabled-password --gecos "" tb-deploy
install -d -m 700 -o tb-deploy -g tb-deploy /home/tb-deploy/.ssh
echo 'PASTE_PUBLIC_KEY_HERE' > /home/tb-deploy/.ssh/authorized_keys
chown tb-deploy:tb-deploy /home/tb-deploy/.ssh/authorized_keys
chmod 600 /home/tb-deploy/.ssh/authorized_keys
```

3. **Docker access.** Membership of the `docker` group is effectively root access. The VPS runs
   only Terrific Bites, so adding `tb-deploy` to it for deployment (`usermod -aG docker
   tb-deploy`) is acceptable once approved, and is what the deployment steps assume. Don't give
   it unrestricted sudo: the few root steps (firewall, Caddy) run from the browser terminal.
   Without the group, discovery still runs but its Docker sections come back empty.

4. Still in the browser terminal, show the server's fingerprint and keep it for part 3:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

## 3. Confirm the server's identity (PowerShell)

```powershell
ssh-keygen -F 2.25.11.35 | Select-Object -First 1
ssh-keyscan -T 10 -t ed25519 2.25.11.35 | ssh-keygen -lf -
```

The second command's `SHA256:` value must **exactly** match the fingerprint from part 2. If it
doesn't, stop.

If the first command prints nothing, this computer hasn't recorded the server yet. Once the
fingerprints match, record it:

```powershell
ssh-keyscan -T 10 -t ed25519 2.25.11.35 | Add-Content "$env:USERPROFILE\.ssh\known_hosts"
```

## 4. Test access and run discovery (PowerShell)

From the repository folder:

```powershell
cd D:\Naushad\Projects\Terrific_Bites

# Tests the login only
powershell -ExecutionPolicy Bypass -File deploy\scripts\Run-VpsDiscovery.ps1 -User tb-deploy -AccessCheckOnly

# Tests the login, then saves the report to vps-report.txt
powershell -ExecutionPolicy Bypass -File deploy\scripts\Run-VpsDiscovery.ps1 -User tb-deploy
```

| Result | Meaning | Next step |
|---|---|---|
| `OK: tb-deploy@...` | Access works | Carry on |
| `Permission denied (publickey)` | The key isn't installed for that user | Repeat part 2 |
| `Host key verification failed` | This computer's record of the server doesn't match | **Stop**, and repeat part 3 |
| `Connection timed out` | Port 22 is blocked, or SSH uses another port | Check **Firewall** and SSH settings in hPanel |

`vps-report.txt` is ignored by Git. The script doesn't read `.env` files, container environment
variables, or anything from the Caddy config other than site names and upstream addresses. It
does list your applications and domains, so skim it before sharing it.

It also records a baseline of what's running. Keep that file to compare against after deployment.

## 5. Individual read-only checks

To run a check on its own, start a session, then use the commands below:

```powershell
ssh -i "$env:USERPROFILE\.ssh\terrific_bites_vps" -o IdentitiesOnly=yes tb-deploy@2.25.11.35
```

| Question | Command |
|---|---|
| CPU, RAM, disk | `nproc; free -h; df -h -x tmpfs -x devtmpfs` |
| Used ports (80, 443, 18010, 18011 and 18069 must be absent) | `ss -ltn` |
| Docker and Compose | `docker version --format '{{.Server.Version}}'; docker compose version` |
| Containers | `docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'` |
| Compose projects | `docker compose ls -a` |
| Container memory use | `docker stats --no-stream --format '{{.Name}} {{.MemUsage}}'` |
| Caddy on the host? | `systemctl is-active caddy; command -v caddy` |
| Caddy in a container? | `docker ps --format '{{.Names}} {{.Image}}' \| grep -i caddy` |
| PostgreSQL on the host? | `systemctl is-active postgresql` |
| PostgreSQL containers | `docker ps --format '{{.Names}} {{.Image}}' \| grep -iE 'postgres\|postgis'` |

DNS can be checked from your own computer:

```powershell
nslookup terrific-bites.trunexus.ai 8.8.8.8               # still Lovable until the cutover
nslookup api.terrific-bites.trunexus.ai 8.8.8.8           # 2.25.11.35 once added
nslookup preview.terrific-bites.trunexus.ai 8.8.8.8       # 2.25.11.35 once added
nslookup -type=NS trunexus.ai 8.8.8.8                     # dns-parking.com means hPanel manages it
```

## 6. What the report has to show before staging

| Check | Needed |
|---|---|
| Free memory | About 4.5 GB: the full stack's limits, including Odoo, add up to about 4.3 GB |
| Free disk | At least 25 GB for images, both databases, the Odoo filestore and 14 days of backups |
| Ports | 18010, 18011 and 18069 free on loopback |
| Docker | Engine and Compose v2 present |
| Ports 80 and 443 | Free, for the host Caddy installed during deployment |
| Caddy | Not installed yet (expected). If one is found, stop and review before installing another |
| Other applications | None expected. Anything found running is reviewed before deployment |
| Rollback | A VPS snapshot is confirmed in hPanel before any deployment |

The report's last section prints `OK` or `INSUFFICIENT` for memory and disk. `INSUFFICIENT` stops
deployment: don't reduce the stack's memory limits to make it fit without a separate decision.

## 7. Removing access

In the browser terminal, as root:

```bash
deluser --remove-home tb-deploy
```

On your computer, delete `terrific_bites_vps` and `terrific_bites_vps.pub` from `.ssh`.

## Email alerts (hPanel)

Only when staging is being set up. `monitor.sh` can send email through a Hostinger mailbox.
Email is not proven until a test message has arrived at the agreed address.

1. In hPanel, go to **Emails**, select **trunexus.ai**, and click **Manage**.
2. Create a mailbox for alerts, or choose an existing one. Hostinger's email plans differ, so
   check that this domain has a mailbox available.
3. Put these in `deploy/.env.prod` on the server. The password stays only there.

```
ALERT_EMAIL_TO=<the address that should receive alerts>
ALERT_EMAIL_FROM=<the mailbox's address>
ALERT_SMTP_URL=smtps://smtp.hostinger.com:465
ALERT_SMTP_USER=<the mailbox's address>
ALERT_SMTP_PASSWORD=<the mailbox's password>
```

4. Send a test, then confirm it arrived, including checking the spam folder:

```bash
scripts/monitor.sh --test-alert
```
