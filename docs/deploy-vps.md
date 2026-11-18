# Deploying to a VPS

The device and your PC reach LaraPaper over the internet through a Cloudflare Tunnel. The droplet
accepts **no inbound connections at all**: cloudflared and Tailscale both connect outward. The
admin UI and SSH are reachable over Tailscale only.

```
device / your PC ──https──> Cloudflare ──tunnel──> cloudflared ──> Caddy ─┬─ device API, rendered images ─> LaraPaper
                                                                          ├─ /api/custom_plugins/* + Bearer token ─> LaraPaper
                                                                          └─ everything else: 404
you (tailnet) ──https──> tailscale serve ──> 127.0.0.1:8080 ──> LaraPaper admin UI
ssh (tailnet) ──> port 22 on tailscale0 only
VPS timer ──> collector container ──http──> larapaper:8080 (weather + GitHub, never leaves the VPS)
```

## 1. Create the infrastructure

Follow [`infra/README.md`](../infra/README.md): Tailscale tag owner and OAuth client, DigitalOcean
and Cloudflare tokens, SSH key, `terraform.tfvars`, then `tofu init`, `tofu plan`, `tofu apply`.
That creates the droplet (with `infra/cloud-init.yaml`), its firewall, the tunnel and the DNS record.

### Tailscale access rules

Replace the default allow-all grant in the tailnet policy:

```json
"tagOwners": { "tag:server": ["autogroup:admin"] },
"grants": [
  { "src": ["autogroup:member"], "dst": ["autogroup:self"], "ip": ["*"] },
  { "src": ["autogroup:member"], "dst": ["tag:server"],     "ip": ["tcp:22", "tcp:443", "icmp:*"] }
],
```

Your devices keep reaching each other; they reach the droplet only on SSH, HTTPS (tailscale serve)
and ping; the droplet can't open connections to anything in the tailnet.

## 2. First login

Wait 5–15 minutes for first boot (package upgrade, Docker, Tailscale). The droplet appears as
`apps` under Machines with the `tag:server` label.

```zsh
ssh -i ~/.ssh/id_ed25519_apps_vps <admin_user>@apps
```

```bash
cloud-init status --long      # status: done, errors: []
sudo finish-setup             # sets your password; sudo asks for it from now on
sudo ufw status verbose       # deny incoming; 22 and 443 only on tailscale0
```

**If `apps` never shows up:** DigitalOcean → droplet → Access → **Recovery Console**, log in with
the password (only after `finish-setup`), and read `/var/log/cloud-init-output.log`. Before
`finish-setup` there's no password; on a fresh droplet it's simpler to recreate it.

**MagicDNS on your laptop:** if `tailscale status` warns that systemd-resolved and NetworkManager are
wired incorrectly, names like `apps` won't resolve. On Ubuntu/Mint:

```zsh
printf '[main]\ndns=systemd-resolved\n' | sudo tee /etc/NetworkManager/conf.d/90-dns-systemd-resolved.conf
sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
sudo systemctl restart systemd-resolved NetworkManager tailscaled
```

Chrome with **Secure DNS** on bypasses the system resolver, so `*.ts.net` names fail there even when
`resolvectl query` works. Set it to "With your current service provider" or off.

**Tailscale SSH instead of OpenSSH (optional):** add an `ssh` rule for `tag:server` in the policy,
then `sudo tailscale set --ssh` on the droplet. Undo with `--ssh=false`.

## 3. Deploy LaraPaper

### `.env`, built on the laptop

From `server/larapaper/` on the laptop. It reuses the laptop's `APP_KEY` (required to read migrated
data), generates the webhook token and takes the tunnel token from tofu, without printing secrets:

```zsh
(umask 077; { grep -E '^(APP_KEY|DASHBOARD_PLUGIN_UUID)=' .env; echo "APP_URL=https://<public_hostname>"; echo "COMPOSE_FILE=compose.prod.yml"; echo "PUBLIC_HOST=<public_hostname>"; echo "WEBHOOK_TOKEN=$(openssl rand -hex 32)"; echo "TUNNEL_TOKEN=$(tofu -chdir=../../infra output -raw tunnel_token)"; } > .env.vps)
```

Add the collector settings (`LAT`, `LON`, `TZ`, `GH_USERNAME`; see `.env.example`) to `.env.vps`
too, or later directly on the VPS.

### Data from the laptop

Stop the laptop's LaraPaper (the device keeps its last screen) and pack both volumes:

```zsh
docker stop larapaper-app-1
mkdir -m 700 -p ~/larapaper-migration
docker run --rm --user root -v larapaper_database:/data/database:ro -v larapaper_storage:/data/storage:ro -v ~/larapaper-migration:/backup --entrypoint tar ghcr.io/usetrmnl/larapaper:0.47.0 czf /backup/volumes.tgz -C /data database storage
scp -i ~/.ssh/id_ed25519_apps_vps ~/larapaper-migration/volumes.tgz .env.vps <admin_user>@apps:/tmp/
```

### On the droplet

As your admin user (`~` is your own home, so use full paths for `apps`):

```bash
sudo -iu apps git clone https://github.com/haguirrear/zectrix-dashboard.git
sudo install -o apps -g apps -m 600 /tmp/.env.vps /home/apps/zectrix-dashboard/server/larapaper/.env
sudo install -o apps -g apps -m 600 /tmp/volumes.tgz /home/apps/volumes.tgz
rm /tmp/.env.vps /tmp/volumes.tgz
```

As `apps`: create containers and volumes without starting them, load the data, then start:

```bash
sudo -iu apps
cd ~/zectrix-dashboard/server/larapaper
docker compose config --quiet && echo env ok
docker compose create
docker run --rm --user root -v larapaper_database:/data/database -v larapaper_storage:/data/storage -v ~/volumes.tgz:/backup/volumes.tgz:ro --entrypoint tar ghcr.io/usetrmnl/larapaper:0.47.0 xzf /backup/volumes.tgz -C /data
docker compose up -d
docker compose ps                         # larapaper: (healthy) after a minute
docker compose logs cloudflared --tail 20
```

`docker compose config --quiet` checks that every required variable is set without printing the
filled-in config (which would show the secrets).

### Admin UI

As your admin user:

```bash
sudo tailscale serve --bg http://127.0.0.1:8080
```

Open the printed `https://apps.<tailnet>.ts.net/` and log in with your existing account.

### Check from outside

```zsh
curl -s -o /dev/null -w '%{http_code}\n' https://<public_hostname>/login                         # 404: admin UI isn't public
curl -s -o /dev/null -w '%{http_code}\n' https://<public_hostname>/api/display                   # 404 from LaraPaper (no device token)
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<public_hostname>/api/custom_plugins/x  # 401: no webhook token
```

A Cloudflare error page (530/1033) instead means cloudflared isn't connected. If curl gets a
Cloudflare challenge page, check Security → Bots / Browser Integrity Check for the zone: the
device and the collector aren't browsers.

## 4. Senders

- **VPS (weather + GitHub):** set `LAT`, `LON`, `TZ`, `GH_USERNAME` in the VPS `.env` and install
  the timer: [`host/vps/README.md`](../host/vps/README.md). It posts to LaraPaper inside the VPS.
- **Your PC (Claude usage + pet):** in `collector/.env`, set
  `LARAPAPER_WEBHOOK_URL=https://<public_hostname>/api/custom_plugins/<plugin-uuid>` and
  `LARAPAPER_WEBHOOK_TOKEN` (the `WEBHOOK_TOKEN` from the VPS `.env`), then limit the timer to
  `SOURCES=claude,pet` ([`host/systemd/README.md`](../host/systemd/README.md)).
- **GitHub Actions** (`collect.yml`) is a fallback and stays off (`COLLECT_ENABLED` unset).

## 5. Point the device

1. In the admin UI, switch on **Permit Auto-Join** (the device may call `/api/setup` again after
   the server change, and LaraPaper only answers known devices while it's on).
2. Hold the button 5–15 seconds (Wi-Fi reset) to open the captive portal. Set your Wi-Fi again and
   **API Server** to `https://<public_hostname>`.
3. Once the device shows the dashboard, switch Auto-Join off.

## 6. Clean up

- Laptop: `rm server/larapaper/.env.vps` and `rm -r ~/larapaper-migration` (a full copy of the data).
- VPS: `rm /home/apps/volumes.tgz` (as `apps`: `rm ~/volumes.tgz`).
- Keep the laptop's LaraPaper stopped (`docker update --restart=no larapaper-app-1` so it doesn't
  come back after a reboot). Remove it once the VPS has run fine for a while.

## Updating

- **Ubuntu:** security updates install automatically; nothing reboots on its own. When
  `/var/run/reboot-required` exists, `sudo reboot` at a convenient time. Docker and Tailscale come
  from their apt repos, so `sudo apt update && sudo apt upgrade` updates them too.
- **LaraPaper, Caddy, cloudflared:** bump the image tags in `compose.prod.yml`, commit, then on the
  VPS as `apps`: `git pull && docker compose up -d`.
- **Collector:** `git pull && docker compose build collector`.
- **Template:** `scripts/push-template.sh` as `apps` on the VPS.

## Backups

All state is in the `larapaper_database` volume (SQLite: devices, plugins, template, users) plus
`larapaper_storage` (rendered images, regenerated anyway). The image has no `sqlite3`, so take a
consistent copy with PHP while it runs:

```bash
docker compose exec -T larapaper php -r '$db = new PDO("sqlite:database/storage/database.sqlite"); $db->exec("VACUUM INTO \"database/storage/backup.sqlite\"");'
docker compose cp larapaper:/var/www/html/database/storage/backup.sqlite ./backup-$(date +%F).sqlite
docker compose exec -T larapaper rm database/storage/backup.sqlite
```

Copy that file off the VPS (e.g. `scp` over Tailscale). DigitalOcean's weekly droplet backups
(`do_backups = true` in `terraform.tfvars`, +20% of the droplet price) are the simple alternative.
