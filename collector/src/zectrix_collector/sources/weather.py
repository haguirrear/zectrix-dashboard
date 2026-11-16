"""Current conditions and today's forecast from Open-Meteo (no API key)."""

from __future__ import annotations

import urllib.parse

from ..http import http_json

WMO = [  # (codes, icon, label)
    ({0}, "sun", "Clear"),
    ({1, 2}, "partly", "Partly cloudy"),
    ({3}, "cloud", "Overcast"),
    ({45, 48}, "fog", "Fog"),
    ({51, 53, 55, 56, 57}, "rain", "Drizzle"),
    ({61, 63, 65, 66, 67, 80, 81, 82}, "rain", "Rain"),
    ({71, 73, 75, 77, 85, 86}, "snow", "Snow"),
    ({95, 96, 99}, "storm", "Thunderstorm"),
]


def describe(code: int) -> tuple[str, str]:
    """WMO weather code -> (icon, label)."""
    return next(((i, label) for codes, i, label in WMO if code in codes), ("cloud", f"Code {code}"))


def collect(cfg: dict) -> dict:
    if not cfg["LAT"] or not cfg["LON"]:
        raise ValueError("LAT/LON are not set")
    q = urllib.parse.urlencode({
        "latitude": cfg["LAT"], "longitude": cfg["LON"], "timezone": cfg["TZ"],
        "temperature_unit": cfg["WEATHER_UNIT"], "forecast_days": 1,
        "current": "temperature_2m,weather_code,apparent_temperature,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
    })
    d = http_json(f"https://api.open-meteo.com/v1/forecast?{q}")
    icon, label = describe(int(d["current"]["weather_code"]))
    rain = d["daily"]["precipitation_probability_max"][0]
    return {
        "temp": round(d["current"]["temperature_2m"]),
        "feels": round(d["current"]["apparent_temperature"]),
        "max": round(d["daily"]["temperature_2m_max"][0]),
        "min": round(d["daily"]["temperature_2m_min"][0]),
        "rain": rain if rain is not None else 0,
        "icon": icon,
        "night": not d["current"].get("is_day", 1),  # Open-Meteo: 1 between sunrise and sunset
        "label": label,
        "unit": "°F" if cfg["WEATHER_UNIT"] == "fahrenheit" else "°C",
    }


def summary(w: dict) -> str:
    return f"{w['temp']}{w['unit']} {w['label']}  {w['min']}–{w['max']}  rain {w['rain']}%"
