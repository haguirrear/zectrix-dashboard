import json
from zoneinfo import ZoneInfo

from zectrix_collector import cli
from zectrix_collector.config import load_config
from zectrix_collector.sinks.larapaper import build_body
from zectrix_collector.sources.claude import from_snapshot

TZ = ZoneInfo("UTC")
KEYS = {"known", "pct", "reset", "resets", "alert"}


def test_claude_windows_always_have_every_key():
    # deep_merge on the server keeps keys we leave out, so every shape must be complete
    now = 1_800_000_000
    snap = {"five_hour": {"used_percentage": 93.4, "resets_at": now + 3600},
            "seven_day": {"used_percentage": 50, "resets_at": now - 1},
            "updated_at": now - 60}
    c = from_snapshot(snap, TZ, now)
    assert c["five_hour"]["pct"] == 93 and c["five_hour"]["alert"] is True
    assert c["seven_day"]["reset"] is True and c["seven_day"]["pct"] == 0
    assert set(c["five_hour"]) == set(c["seven_day"]) == KEYS
    assert set(from_snapshot({}, TZ, now)["five_hour"]) == KEYS
    assert c["stale"] is False


def test_larapaper_body_uses_deep_merge():
    body = json.loads(build_body({"weather": {"temp": 3}}))
    assert body == {"merge_variables": {"weather": {"temp": 3}}, "merge_strategy": "deep_merge"}


def test_failed_source_is_left_out(monkeypatch):
    class Boom:
        @staticmethod
        def collect(cfg):
            raise RuntimeError("offline")

    class Ok:
        @staticmethod
        def collect(cfg):
            return {"x": 1}

    monkeypatch.setitem(cli.SOURCES, "weather", Boom)
    monkeypatch.setitem(cli.SOURCES, "github", Ok)
    data, failed = cli.collect(["weather", "github"], {"TZ": "UTC"})
    assert failed == ["weather"]
    assert "weather" not in data and data["github"] == {"x": 1}
    assert {"date", "updated"} <= set(data)


def test_env_vars_override_file_but_empty_ones_dont(tmp_path, monkeypatch):
    env = tmp_path / "x.env"
    env.write_text("LAT=1.5\nTZ=Europe/Madrid\n# comment\n")
    monkeypatch.setenv("LAT", "2.5")
    monkeypatch.setenv("TZ", "")
    cfg = load_config(str(env))
    assert cfg["LAT"] == "2.5" and cfg["TZ"] == "Europe/Madrid"
