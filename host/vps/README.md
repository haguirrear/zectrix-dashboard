# systemd timer (VPS)

Sends weather and GitHub data every 15 minutes. It starts the `collector` service from
`server/larapaper/compose.prod.yml`, which collects, posts to LaraPaper over the compose network
and exits. No container stays running between runs (`docker compose ps` won't list it).

Claude usage and the pet photo still come from your PC (`host/systemd/`, with `SOURCES=claude,pet`).

## Setup

1. In `server/larapaper/.env` on the VPS, set `LAT`, `LON`, `TZ` and `GH_USERNAME`
   (see `.env.example`). `DASHBOARD_PLUGIN_UUID` must be set too: it builds the webhook URL.
2. As `apps`, build the image and try one run:
   ```bash
   cd ~/zectrix-dashboard/server/larapaper
   docker compose build collector
   docker compose run --rm collector --only weather,github --dry-run
   docker compose run --rm collector
   ```
3. As your admin user, install and start the timer:
   ```bash
   sudo install -m 644 /home/apps/zectrix-dashboard/host/vps/zectrix-collector.service /home/apps/zectrix-dashboard/host/vps/zectrix-collector.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now zectrix-collector.timer
   ```

The units are copied rather than linked, so after a `git pull` that changes them, run the
`install` and `daemon-reload` again.

## Day to day

- Last runs: `journalctl -u zectrix-collector.service -n 30`
- Next run: `systemctl list-timers zectrix-collector.timer`
- Run now: `sudo systemctl start zectrix-collector.service`
- After a `git pull` that changes `collector/`: `docker compose build collector` (as `apps`).
