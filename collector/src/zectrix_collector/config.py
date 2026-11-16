"""Configuration: defaults < .env file < environment variables.

The .env file is looked up in this order: --env argument, $ZECTRIX_ENV, collector/.env.
In GitHub Actions there is no file; everything comes from secrets/variables as env vars.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # collector/

DEFAULTS: dict[str, str] = {
    # Sink
    "SINK": "larapaper",
    "LARAPAPER_WEBHOOK_URL": "",
    "LARAPAPER_WEBHOOK_TOKEN": "",  # sent as "Authorization: Bearer ..." when set (checked by the Caddy proxy)
    # Weather (Open-Meteo, no key)
    "LAT": "",
    "LON": "",
    "TZ": "UTC",
    "WEATHER_UNIT": "celsius",  # or fahrenheit
    # GitHub
    "GH_LOGIN": "",  # empty = the account the `gh` CLI is logged in as
    "GH_WEEKS": "18",
    "HEATMAP_STYLE": "stripes",  # "stripes" (diagonal hatching) or "dither" (25/50/75% ordered dither)
    "GH_SOURCE": "public",  # public = profile page as a logged-out visitor sees it; api = GraphQL via gh
    # Claude Code usage snapshot written by host/claude-code/claude_usage_tap.py
    "CLAUDE_USAGE_FILE": "~/.cache/claude-usage.json",
    # Pet photo
    "PET_PHOTO": "",
    "PET_FOCUS": "0.5,0.42",
    "PET_ZOOM": "1.5",  # >1 crops tighter around the focus point
    "PET_SIZE": "140x300",
}


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config(env_file: str | None = None) -> dict[str, str]:
    cfg = dict(DEFAULTS)
    path = Path(env_file or os.environ.get("ZECTRIX_ENV") or PROJECT_DIR / ".env").expanduser()
    if path.exists():
        cfg.update(parse_env_file(path))
    elif env_file:
        raise FileNotFoundError(f"config file not found: {path}")
    for k in list(cfg):
        if os.environ.get(k):  # empty env vars (e.g. an unset Actions variable) don't override
            cfg[k] = os.environ[k]
    return cfg
