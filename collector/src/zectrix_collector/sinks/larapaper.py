"""Push to a LaraPaper webhook plugin (POST /api/custom_plugins/<plugin-uuid>).

Uses merge_strategy=deep_merge so several senders (GitHub Actions: weather + github;
your PC: claude + pet) each update only their own keys without erasing the others'.
A section that failed to collect is simply not sent, so the screen keeps its last good value.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..http import USER_AGENT


def build_body(data: dict) -> bytes:
    return json.dumps({"merge_variables": data, "merge_strategy": "deep_merge"}).encode()


def send(data: dict, cfg: dict) -> str:
    url = cfg["LARAPAPER_WEBHOOK_URL"]
    if not url:
        raise ValueError("LARAPAPER_WEBHOOK_URL is not set")
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT}
    if cfg.get("LARAPAPER_WEBHOOK_TOKEN"):
        headers["Authorization"] = f"Bearer {cfg['LARAPAPER_WEBHOOK_TOKEN']}"
    req = urllib.request.Request(url, data=build_body(data), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return f"HTTP {r.status} {r.read()[:200].decode(errors='replace')}"
    except urllib.error.HTTPError as e:  # don't echo the URL: it contains the plugin uuid
        detail = e.read()[:200].decode(errors="replace")
        raise RuntimeError(f"LaraPaper rejected the payload: HTTP {e.code} {detail}") from None
