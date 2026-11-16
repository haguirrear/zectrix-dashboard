"""GitHub contribution calendar -> Monday-first heatmap PNG plus totals and streak."""

from __future__ import annotations

import base64
import json
import re
import subprocess
from datetime import date

from ..http import http_get
from ..render.heatmap import heatmap_png

Day = tuple[str, int, int]  # (ISO date, contribution count, level 0-4)

GQL = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def quartile_levels(counts: list[int]) -> list[int]:
    """GitHub-style 0-4 levels: 0 = none, 1-4 = quartiles of the non-zero days."""
    nz = sorted(c for c in counts if c > 0)
    if not nz:
        return [0] * len(counts)
    q = [nz[min(len(nz) - 1, int(len(nz) * f))] for f in (0.25, 0.5, 0.75)]
    return [0 if c == 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4 for c in counts]


def days_api(login: str) -> tuple[list[Day], int]:
    """Per-day data via GraphQL with the `gh` CLI. Omits private contributions to orgs the gh
    token isn't authorized for (e.g. SAML SSO orgs), so it can undercount."""
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={GQL}", "-F", f"login={login}"],
                         capture_output=True, text=True, check=True).stdout
    cal = json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    raw = [(d["date"], d["contributionCount"]) for wk in cal["weeks"] for d in wk["contributionDays"]]
    levels = quartile_levels([c for _, c in raw])
    return [(d, c, lv) for (d, c), lv in zip(raw, levels, strict=True)], cal["totalContributions"]


def parse_public_calendar(html: str) -> tuple[list[Day], int]:
    """Parse the public profile calendar (undocumented HTML): cells carry data-date, data-level
    (GitHub's 0-4 shade) and an id; <tool-tip for=id> holds "N contributions on ..."."""
    cells = {}  # id -> (date, level)
    for td in re.findall(r"<td\b[^>]*\bdata-date=\"[^\"]+\"[^>]*>", html):
        d, i = re.search(r'data-date="([^"]+)"', td), re.search(r'\bid="([^"]+)"', td)
        lv = re.search(r'data-level="(\d)"', td)
        if d and i:
            cells[i.group(1)] = (d.group(1), int(lv.group(1)) if lv else 0)
    if not cells:
        raise RuntimeError("contribution calendar not found in public page (layout changed?)")
    counts = {}
    for for_id, text in re.findall(r"<tool-tip\b[^>]*\bfor=\"([^\"]+)\"[^>]*>([^<]*)</tool-tip>", html):
        if for_id in cells:
            m = re.match(r"\s*(\d+)\s+contribution", text)
            counts[cells[for_id][0]] = int(m.group(1)) if m else 0
    days = sorted((d, counts.get(d, 0), lv) for d, lv in cells.values())
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    total = int(m.group(1).replace(",", "")) if m else sum(c for _, c, _ in days)
    return days, total


def days_public(login: str) -> tuple[list[Day], int]:
    """What a logged-out visitor sees (includes anonymized private contributions when the
    profile setting is on). Needs no token, so it works from CI."""
    html = http_get(f"https://github.com/users/{login}/contributions").decode("utf-8", "replace")
    return parse_public_calendar(html)


def week_grid(days: list[Day], nweeks: int) -> tuple[list[list[Day]], list[list[int]]]:
    """Group days into Monday-first weeks (columns; rows = Mon..Sun) and keep the last `nweeks`.
    Returns (weeks, level grid) where -1 marks cells that aren't drawn (partial first/last week)."""
    weeks: list[list[Day]] = []
    for day in days:
        if not weeks or date.fromisoformat(day[0]).weekday() == 0:  # Monday starts a new column
            weeks.append([])
        weeks[-1].append(day)
    weeks = weeks[-nweeks:]
    grid = [[lv for _, _, lv in wk] + [-1] * (7 - len(wk)) for wk in weeks]
    if weeks and len(weeks[0]) < 7:  # a partial first week belongs at the bottom of its column
        grid[0] = [-1] * (7 - len(weeks[0])) + [lv for _, _, lv in weeks[0]]
    return weeks, grid


def current_streak(days: list[Day]) -> int:
    """Consecutive active days ending today; today itself may still be empty."""
    streak = 0
    for i, (_, c, _) in enumerate(reversed(days)):
        if c > 0:
            streak += 1
        elif i > 0:
            break
    return streak


def collect(cfg: dict) -> dict:
    login = cfg["GH_LOGIN"] or subprocess.run(
        ["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, check=True).stdout.strip()
    source = cfg["GH_SOURCE"].lower()
    days, total = days_public(login) if source == "public" else days_api(login)
    weeks, grid = week_grid(days, int(cfg["GH_WEEKS"]))
    png, w, h = heatmap_png(grid, style=cfg["HEATMAP_STYLE"].lower())
    return {"login": login, "source": source, "total": total,
            "period_total": sum(c for wk in weeks for _, c, _ in wk),
            "streak": current_streak(days), "nweeks": len(grid), "levels": grid,
            "heatmap": {"src": "data:image/png;base64," + base64.b64encode(png).decode(),
                        "width": w, "height": h}}


def summary(g: dict) -> str:
    return f"{g['login']}: {g['total']} this year, {g['period_total']} in {g['nweeks']} weeks, streak {g['streak']}"
