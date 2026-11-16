"""Data sources. Each module exposes collect(cfg) -> dict (raises on failure) and summary(dict) -> str.

The dict becomes one top-level key of the payload, e.g. {{ weather.temp }} in the template.
See schema/dashboard.schema.json for the shapes.
"""

from . import claude, github, pet, weather

SOURCES = {"weather": weather, "github": github, "claude": claude, "pet": pet}
