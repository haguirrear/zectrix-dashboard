from __future__ import annotations

import json
import urllib.request

USER_AGENT = "zectrix-dashboard/0.1"


def http_get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url: str, timeout: int = 20) -> dict:
    return json.loads(http_get(url, timeout))
