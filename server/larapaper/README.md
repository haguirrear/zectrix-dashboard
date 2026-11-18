# LaraPaper (TRMNL BYOS server)

Self-hosted [LaraPaper](https://github.com/usetrmnl/larapaper) renders the dashboard for the
ZECTRIX NOTE4C (400×300, black/white/red/yellow) running our TRMNL firmware fork.

| File | Purpose |
|---|---|
| `compose.yml` | local / LAN setup (plain HTTP on port 4567) |
| `compose.prod.yml` + `Caddyfile` | VPS setup, see [`docs/deploy-vps.md`](../../docs/deploy-vps.md) |
| `templates/dashboard.liquid` | the dashboard layout (source of truth; push it with the script below) |
| `scripts/push-template.sh` | copies the template into the plugin, re-renders it, and backs up the previous version |
| `.env.example` | copy to `.env` (gitignored) |

## Local setup

### 1. `.env`

```zsh
cp .env.example .env
```

Then set:
- `APP_KEY`: generate it with `echo "base64:$(openssl rand -base64 32)"`. Keep it stable once data exists, because it encrypts stored secrets.
- `APP_URL=http://<laptop-lan-ip>:4567`: the device downloads images from this address, so not `localhost`. A DHCP reservation on the router keeps it stable.

### 2. Start

```zsh
docker compose up -d
```

UI: `http://<laptop-lan-ip>:4567`. Register the first account; signup closes after that.

**Security:** this is plain HTTP for the home LAN. Never port-forward it on the router.
Docker-published ports bypass ufw rules.

### 3. Device model for the NOTE4C

LaraPaper ships built-in device models and palettes. In **Device Models** (`/device-models`),
duplicate **Waveshare 7.5" B/W/R/Y** (`waveshare_7_5_bwry`) or create a new one:

- Name `zectrix_note4c_bwry`, Width `400`, Height `300`, Colors `2`, Bit Depth `1`, Scale `1`,
  Rotation `0`, MIME `image/png`.
- Color Palette: **Color (4 colors: black, red, white, yellow)** (`color-4bwry`).

After the device appears, set its Device Model to this one.

### 4. Connect the NOTE4C

1. In the LaraPaper header, switch on **Permit Auto-Join**. It only works while exactly one user exists.
2. Open the device's captive portal and set **API Server** to `http://<laptop-lan-ip>:4567`
   (no trailing slash).
3. The device calls `/api/setup` and appears under **Devices**. Switch Auto-Join off again, then
   assign the NOTE4C device model.

### 5. Dashboard plugin

1. Create a **webhook** plugin and assign it to the device's playlist.
2. Put its uuid in `.env` as `DASHBOARD_PLUGIN_UUID`. The uuid is secret: anyone who has it can write to the screen.
3. Push the template:
   ```zsh
   scripts/push-template.sh
   ```
4. Set `LARAPAPER_WEBHOOK_URL=http://<laptop-lan-ip>:4567/api/custom_plugins/<uuid>` in
   `collector/.env`.

## Editing the template

Edit `templates/dashboard.liquid`, then run `scripts/push-template.sh`. The script:
- saves the previous markup to `backups/` (gitignored);
- re-renders and prints the new image id.

The rendered PNG is at `storage/app/public/images/generated/<id>.png` inside the container:

```zsh
docker compose cp larapaper:/var/www/html/storage/app/public/images/generated/<id>.png /tmp/screen.png
```

Template variables are documented in [`schema/dashboard.schema.json`](../../schema/dashboard.schema.json).
Also available: `trmnl.device.percent_charged` and `trmnl.device.wifi_strength` (0–3).

## Upgrading LaraPaper

The image is pinned (`ghcr.io/usetrmnl/larapaper:0.47.0`) in both compose files. To upgrade:
1. Bump the tag.
2. Run `docker compose pull && docker compose up -d`.
3. Check that the screen still renders: `scripts/push-template.sh` re-renders it.
