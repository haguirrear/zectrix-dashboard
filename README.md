# zectrix-dashboard

A self-hosted e-ink dashboard for the **ZECTRIX NOTE4C** (ESP32-S3, 4.2" 400×300
black/white/red/yellow e-paper). It shows the weather, a GitHub contribution graph, Claude Code
plan usage and a pet photo, and refreshes every few minutes on battery.

```
firmware/trmnl/    TRMNL firmware fork (git subtree) with NOTE4C fixes       → the device
server/larapaper/  LaraPaper (TRMNL BYOS server): template, compose, Caddy   → laptop / VPS
collector/         Python package that gathers data and pushes it            → VPS + PC
host/              systemd timers (PC, VPS), Claude Code usage tap           → your PC, VPS
infra/             OpenTofu: droplet, firewall, Cloudflare Tunnel, DNS        → your laptop
schema/            the data contract between collector and template
docs/              architecture, hardware, flashing, device API, VPS deploy
```

Start with [`docs/architecture.md`](docs/architecture.md).

## Quick start (everything on your laptop)

1. **Server:** follow [`server/larapaper/README.md`](server/larapaper/README.md): `.env`, then
   `docker compose up -d`, then create the device model and the webhook plugin, then
   `scripts/push-template.sh`.
2. **Firmware:** `just fw-build`, then flash it ([`docs/flashing.md`](docs/flashing.md)). In the
   device's captive portal, set your Wi-Fi and the API Server `http://<laptop-ip>:4567`.
3. **Data:** set up `collector/.env` from `.env.example`, then run `just collect-dry` and `just collect`.
4. **Every 5 minutes:** install the timer ([`host/systemd/README.md`](host/systemd/README.md)).
   For Claude usage, add the status-line tap ([`host/claude-code/README.md`](host/claude-code/README.md)).

Moving to a VPS: [`docs/deploy-vps.md`](docs/deploy-vps.md). After the move, the VPS sends
weather and GitHub data itself, so the screen stays fresh while your laptop is off.

## Secrets

Nothing secret is committed. Only `*.env.example` files are tracked.

| Secret | Lives in |
|---|---|
| LaraPaper `APP_KEY`, plugin uuid, webhook token, tunnel token, your location (VPS) | `server/larapaper/.env` |
| Webhook URL + token, your location (PC) | `collector/.env` |
| Cloud API tokens, state passphrase | `infra/terraform.tfvars`; encrypted `infra/terraform.tfstate` |
| Factory flash dump, pet photo | outside the repo |

Every CI run scans for secrets (gitleaks over the full history). Locally, run `pre-commit install`
once to scan each commit.

## License

MIT (see [LICENSE](LICENSE)), except `firmware/trmnl/`, which is GPL-3.0 like the TRMNL firmware
it comes from.
