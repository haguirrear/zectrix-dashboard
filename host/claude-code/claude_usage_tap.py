#!/usr/bin/env python3
"""Save Claude plan rate-limit usage from Claude Code's status-line JSON.

Claude Code pipes a JSON object to the configured status-line command on stdin.
For claude.ai Pro/Max/Ultra subscribers it contains (after the first response):

    "rate_limits": {
      "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
      "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}
    }

Docs: https://code.claude.com/docs/en/statusline (rate_limits fields).
Each window may be absent. This script writes what is present, plus a timestamp,
to ~/.cache/claude-usage.json (atomically) so the dashboard collector can read it.

Usage (from an existing status-line script, without changing its output):
    input=$(cat)
    printf '%s' "$input" | python3 /path/to/zectrix-dashboard/host/claude-code/claude_usage_tap.py
Prints nothing; never fails the status line.
"""

import json
import os
import sys
import tempfile
import time

CACHE = os.path.expanduser(os.environ.get("CLAUDE_USAGE_FILE", "~/.cache/claude-usage.json"))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    limits = data.get("rate_limits") or {}
    windows = {}
    for name in ("five_hour", "seven_day"):
        w = limits.get(name)
        if isinstance(w, dict) and "used_percentage" in w:
            windows[name] = {"used_percentage": w.get("used_percentage"), "resets_at": w.get("resets_at")}
    if not windows:
        return  # nothing new; keep the previous snapshot
    # Merge with the previous snapshot so a window that is temporarily absent isn't lost.
    try:
        with open(CACHE) as f:
            prev = json.load(f)
    except Exception:
        prev = {}
    snapshot = {**{k: v for k, v in prev.items() if k in ("five_hour", "seven_day")}, **windows,
                "updated_at": int(time.time())}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CACHE), prefix=".claude-usage-")
    with os.fdopen(fd, "w") as f:
        json.dump(snapshot, f)
    os.replace(tmp, CACHE)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a status line must never break
