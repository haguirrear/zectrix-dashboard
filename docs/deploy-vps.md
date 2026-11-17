# Deploying LaraPaper to a VPS

Goal: the device and the data senders reach the server over the internet. Only what they need is
public. The admin UI and SSH are reachable over Tailscale only.

```
internet ──443──> Caddy ─┬─ /api/setup, /api/display, /api/log, /api/current_screen, /storage/images/*  ─> LaraPaper
                         ├─ /api/custom_plugins/*  (requires Bearer token)                                ─> LaraPaper
                         └─ everything else: 404
tailnet  ──443──> Caddy (bound to the Tailscale IP, *.ts.net cert) ─> LaraPaper admin UI
```

## 1. VPS

- 2 GB RAM. LaraPaper renders screens with headless Chromium, and 1 GB runs out of memory.
  Ubuntu 24.04 LTS or Debian 12.
- Install Docker (`curl -fsSL https://get.docker.com | sh`) and Tailscale
  (`curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up --ssh`).
- In the Tailscale admin console, enable **MagicDNS** and **HTTPS certificates**.
- Firewall: open 80/tcp and 443/tcp only, and close 22. Use Tailscale SSH (`ssh user@<vps>.ts.net`).
  ```zsh
  sudo ufw default deny incoming
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow in on tailscale0
  sudo ufw enable
  ```
  Port 80 is only used for the Let's Encrypt HTTP challenge and redirects to HTTPS.

## 2. DNS

Create an `A` record for `PUBLIC_HOST` (e.g. `eink.example.com`) pointing to the VPS's public IP.

## 3. Deploy

```zsh
git clone https://github.com/<you>/zectrix-dashboard.git
cd zectrix-dashboard/server/larapaper
cp .env.example .env
```

Fill in `.env`:

| Key | Value |
|---|---|
| `APP_KEY` | the **same** key as the laptop's if you migrate data, else `echo "base64:$(openssl rand -base64 32)"` |
| `APP_URL` | `https://<PUBLIC_HOST>` |
| `PUBLIC_HOST` | `eink.example.com` |
| `ADMIN_HOST` | `<vps-name>.<tailnet>.ts.net` (`tailscale status --json \| jq -r .Self.DNSName`, without the trailing dot) |
| `TAILSCALE_IP` | `tailscale ip -4` |
| `WEBHOOK_TOKEN` | `openssl rand -hex 32` |
| `ACME_EMAIL` | your email, for certificate expiry notices |
| `DASHBOARD_PLUGIN_UUID` | after step 4 |

```zsh
docker compose -f compose.prod.yml up -d
docker compose -f compose.prod.yml logs -f caddy
```

## 4. Data: migrate or start fresh

**Fresh:**
1. Open `https://<ADMIN_HOST>` from a device on your tailnet and register the first account.
2. Create the device model (see `server/larapaper/README.md`).
3. Create a webhook plugin and note its uuid.
4. Push the template: `COMPOSE_FILE=compose.prod.yml scripts/push-template.sh`.

**Migrate from the laptop.** Copy the SQLite database and generated images, keeping the same `APP_KEY`:

```zsh
docker run --rm -v larapaper_database:/data -v "$PWD":/out alpine tar czf /out/larapaper-db.tgz -C /data .
```

Copy the archive to the VPS, then extract it into the `larapaper_database` volume before the
first `up`. Device, plugin uuid and template all come along.

## 5. Point the senders and the device

- **GitHub Actions** (repo → Settings → Secrets and variables → Actions):
  - secrets: `LARAPAPER_WEBHOOK_URL=https://<PUBLIC_HOST>/api/custom_plugins/<uuid>` and `LARAPAPER_WEBHOOK_TOKEN`;
  - variables: `LAT`, `LON`, `TZ`, `GH_USERNAME`, then `COLLECT_ENABLED=true`.
- **Your PC:** set the same URL and token in `collector/.env`. Limit the timer to `SOURCES=claude,pet`
  (see `host/systemd/README.md`).
- **The device:** open the captive portal (hold the button combo, or let Wi-Fi fail) and set the
  API Server to `https://<PUBLIC_HOST>`. If it was registered on the laptop's LaraPaper, turn on
  Permit Auto-Join on the new server first, unless you migrated the database.

## 6. Check

```zsh
curl -s -o /dev/null -w '%{http_code}\n' https://<PUBLIC_HOST>/login
```

Expect `404`, because the admin UI isn't public.

```zsh
curl -s -o /dev/null -w '%{http_code}\n' https://<PUBLIC_HOST>/api/custom_plugins/<uuid>
```

Expect `401`, because there's no token.

```zsh
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer <token>" https://<PUBLIC_HOST>/api/custom_plugins/<uuid>
```

Expect `200`.

## Backups

Everything lives in the `larapaper_database` volume (SQLite: devices, plugins, template, users).
Use the provider's snapshots, or run a nightly
`docker run --rm -v larapaper_database:/data -v /root/backups:/out alpine tar czf /out/db-$(date +%F).tgz -C /data .`
plus an off-site copy.

## Later: Cloudflare in front

See the notes at the end of `server/larapaper/Caddyfile`. Because the firmware doesn't verify
certificates (`docs/device-api.md`), Cloudflare's certificate works for the device without firmware changes.
