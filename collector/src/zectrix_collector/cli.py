"""Collect dashboard data and push it to the e-ink server.

Sources: weather (Open-Meteo), github (contribution calendar), claude (Claude Code plan usage,
PC only), pet (photo, PC only). Every run also sends "date" and "updated".

Examples (from collector/):
  uv run zectrix-collect --dry-run                       # collect everything, print, don't send
  uv run zectrix-collect --only weather,github           # what the VPS runs (host/vps/)
  uv run zectrix-collect --only claude,pet               # what your PC runs once the server is remote
  uv run zectrix-collect --out /tmp/payload.json         # also save the payload

Config: collector/.env (see .env.example), --env FILE, or environment variables.
Exit status is 1 if any requested source failed (the others are still sent).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_config
from .sinks import SINKS
from .sources import SOURCES


def collect(names: list[str], cfg: dict) -> tuple[dict, list[str]]:
    now = datetime.now(ZoneInfo(cfg["TZ"]))
    data: dict = {"updated": now.strftime("%H:%M"), "date": now.strftime("%a %b ") + str(now.day)}
    failed = []
    for name in names:
        try:
            data[name] = SOURCES[name].collect(cfg)
        except Exception as e:  # one failing source must not block the rest
            print(f"[warn] {name}: {e} (not sent; the screen keeps its previous value)", file=sys.stderr)
            failed.append(name)
    return data, failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zectrix-collect", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=",".join(SOURCES),
                    help=f"comma-separated sources to collect (default: all = {','.join(SOURCES)})")
    ap.add_argument("--dry-run", action="store_true", help="collect and print, don't send")
    ap.add_argument("--out", help="also write the collected data as JSON to this file")
    ap.add_argument("--env", help="config file (default: $ZECTRIX_ENV or collector/.env)")
    a = ap.parse_args(argv)

    names = [n.strip() for n in a.only.split(",") if n.strip()]
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        ap.error(f"unknown source(s): {', '.join(unknown)}; choose from {', '.join(SOURCES)}")

    cfg = load_config(a.env)
    data, failed = collect(names, cfg)

    print(f"{'date':<8} {data['date']}  updated {data['updated']}")
    for name in names:
        if name in data:
            print(f"{name:<8} {SOURCES[name].summary(data[name])}")

    sink = SINKS[cfg["SINK"]]
    if a.out:
        Path(a.out).write_text(sink.build_body(data).decode() if hasattr(sink, "build_body") else str(data))
    if not a.dry_run:
        print(f"{'sent':<8} {sink.send(data, cfg)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
