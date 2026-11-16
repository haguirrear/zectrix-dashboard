"""Contract test: what the sources produce matches schema/dashboard.schema.json (what the template reads)."""

import json
from pathlib import Path

import jsonschema
import pytest
from PIL import Image

from zectrix_collector import cli
from zectrix_collector.sources import github, pet, weather

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schema" / "dashboard.schema.json").read_text())

OPEN_METEO = {
    "current": {"temperature_2m": 9.6, "apparent_temperature": 7.2, "weather_code": 61, "is_day": 0},
    "daily": {"temperature_2m_max": [14.2], "temperature_2m_min": [2.4], "precipitation_probability_max": [None],
              "weather_code": [61]},
}


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    photo = tmp_path / "pet.png"
    Image.new("RGB", (60, 80), (200, 120, 40)).save(photo)
    snap = tmp_path / "claude.json"
    snap.write_text(json.dumps({"five_hour": {"used_percentage": 12.0, "resets_at": 4_000_000_000},
                                "updated_at": 1_800_000_000}))
    monkeypatch.setattr(weather, "http_json", lambda url: OPEN_METEO)
    days = [(f"2026-10-{d:02d}", d % 3, d % 5) for d in range(1, 32)]
    monkeypatch.setattr(github, "days_public", lambda login: (days, 123))
    return {"TZ": "America/New_York", "LAT": "1", "LON": "2", "WEATHER_UNIT": "celsius",
            "GH_LOGIN": "octocat", "GH_SOURCE": "public", "GH_WEEKS": "18", "HEATMAP_STYLE": "stripes",
            "CLAUDE_USAGE_FILE": str(snap), "PET_PHOTO": str(photo), "PET_FOCUS": "0.5,0.5", "PET_ZOOM": "1",
            "PET_SIZE": "14x30"}


def test_collected_payload_matches_schema(cfg):
    data, failed = cli.collect(list(cli.SOURCES), cfg)
    assert failed == []
    jsonschema.validate(data, SCHEMA)
    assert data["weather"]["rain"] == 0 and data["weather"]["night"] is True
    assert data["pet"]["width"] == 14


def test_schema_rejects_an_incomplete_usage_window(cfg):
    data, _ = cli.collect(["claude"], cfg)
    del data["claude"]["five_hour"]["alert"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, SCHEMA)


def test_pet_source_is_registered():
    assert cli.SOURCES["pet"] is pet
