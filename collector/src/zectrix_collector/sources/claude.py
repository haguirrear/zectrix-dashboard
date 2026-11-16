"""Claude plan usage (5-hour and 7-day windows) from the snapshot that
host/claude-code/claude_usage_tap.py saves from Claude Code's status line. Runs on your PC only."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

STALE_AFTER_MIN = 300


def window(snap: dict, name: str, fmt: str, tz: ZoneInfo, now: float) -> dict:
    # Always return every key: the server deep-merges payloads, so a key left out would keep
    # its previous value (e.g. a stale "alert").
    w = snap.get(name)
    if not w or w.get("used_percentage") is None:
        return {"known": False, "pct": 0, "reset": False, "resets": "", "alert": False}
    resets = w.get("resets_at")
    if resets and resets <= now:  # window already rolled over since the snapshot
        return {"known": True, "pct": 0, "reset": True, "resets": "now", "alert": False}
    pct = round(float(w["used_percentage"]))
    when = datetime.fromtimestamp(resets, tz).strftime(fmt) if resets else ""
    return {"known": True, "pct": pct, "reset": False, "resets": when,
            "alert": pct >= 90}  # red only when really close to the limit


def from_snapshot(snap: dict, tz: ZoneInfo, now: float) -> dict:
    updated = snap.get("updated_at", now)
    return {"available": True,
            "five_hour": window(snap, "five_hour", "%H:%M", tz, now),
            "seven_day": window(snap, "seven_day", "%a %H:%M", tz, now),
            "asof": datetime.fromtimestamp(updated, tz).strftime("%H:%M"),
            "stale": (now - updated) / 60 > STALE_AFTER_MIN}


def collect(cfg: dict) -> dict:
    path = Path(os.path.expanduser(cfg["CLAUDE_USAGE_FILE"]))
    if not path.exists():
        raise FileNotFoundError(f"no usage snapshot yet at {path} (see host/claude-code/)")
    return from_snapshot(json.loads(path.read_text()), ZoneInfo(cfg["TZ"]), time.time())


def summary(c: dict) -> str:
    def fmt(w: dict) -> str:
        return f"{w['pct']}% (resets {w['resets']})" if w["known"] else "–"
    return f"5h {fmt(c['five_hour'])}  7d {fmt(c['seven_day'])}  as of {c['asof']}"
