"""Load and validate a Heatline country configuration.

Everything country-specific lives in one YAML file (see config/jamaica.yaml):
locations, alert thresholds, language, emergency numbers, channels. Adapting
Heatline to a new country means writing a new config file, not new code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml


class ConfigError(ValueError):
    """Raised when a configuration file is missing, malformed or unsafe."""


@dataclass(frozen=True)
class AlertLevel:
    name: str
    hi_c: float
    min_consecutive_hours: int


@dataclass(frozen=True)
class Location:
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class CountryConfig:
    country: str
    timezone: str
    language: str
    emergency: Dict[str, str]
    day_start_hour: int  # daytime window considered for alerts, inclusive
    day_end_hour: int
    levels: List[AlertLevel]  # sorted most severe first
    forecast_days: int
    locations: List[Location]
    channels: List[str]


def load_config(path) -> CountryConfig:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}")
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: config root must be a mapping")

    _require(raw, ["country", "timezone", "language", "emergency", "alert_levels", "locations"], path)

    levels = _parse_levels(raw["alert_levels"], path)
    locations = _parse_locations(raw["locations"], path)

    emergency = raw["emergency"]
    if not isinstance(emergency, dict) or not emergency:
        raise ConfigError(f"{path}: 'emergency' must be a non-empty mapping of service -> number")
    emergency = {str(k): str(v) for k, v in emergency.items()}

    day_window = raw.get("day_window", {})
    day_start = int(day_window.get("start_hour", 8))
    day_end = int(day_window.get("end_hour", 18))
    if not (0 <= day_start < day_end <= 23):
        raise ConfigError(f"{path}: day_window must satisfy 0 <= start_hour < end_hour <= 23")

    forecast = raw.get("forecast", {})
    forecast_days = int(forecast.get("days", 7))
    if not 1 <= forecast_days <= 16:
        raise ConfigError(f"{path}: forecast.days must be between 1 and 16")

    channels = [str(c) for c in raw.get("channels", ["console"])]

    return CountryConfig(
        country=str(raw["country"]),
        timezone=str(raw["timezone"]),
        language=str(raw["language"]),
        emergency=emergency,
        day_start_hour=day_start,
        day_end_hour=day_end,
        levels=levels,
        forecast_days=forecast_days,
        locations=locations,
        channels=channels,
    )


def _require(mapping: dict, keys: List[str], path) -> None:
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ConfigError(f"{path}: missing required key(s): {', '.join(missing)}")


def _parse_levels(entries, path) -> List[AlertLevel]:
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: 'alert_levels' must be a non-empty list")
    levels = []
    for item in entries:
        try:
            level = AlertLevel(
                name=str(item["name"]).strip().lower(),
                hi_c=float(item["hi_c"]),
                min_consecutive_hours=int(item.get("min_consecutive_hours", 1)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"{path}: bad alert level entry {item!r}: {exc}")
        if not 25.0 <= level.hi_c <= 60.0:
            raise ConfigError(
                f"{path}: alert threshold {level.hi_c} °C is outside the sane range 25-60 °C"
            )
        if level.min_consecutive_hours < 1:
            raise ConfigError(f"{path}: min_consecutive_hours must be >= 1 for level {level.name!r}")
        if "|" in level.name or not level.name:
            raise ConfigError(f"{path}: alert level names must be non-empty and must not contain '|'")
        levels.append(level)
    names = [level.name for level in levels]
    if len(set(names)) != len(names):
        raise ConfigError(f"{path}: duplicate alert level names: {names}")
    return sorted(levels, key=lambda level: level.hi_c, reverse=True)


def _parse_locations(entries, path) -> List[Location]:
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: 'locations' must be a non-empty list")
    locations = []
    for item in entries:
        try:
            loc = Location(name=str(item["name"]).strip(), lat=float(item["lat"]), lon=float(item["lon"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"{path}: bad location entry {item!r}: {exc}")
        if not loc.name or "|" in loc.name:
            raise ConfigError(f"{path}: location names must be non-empty and must not contain '|'")
        if not -90.0 <= loc.lat <= 90.0 or not -180.0 <= loc.lon <= 180.0:
            raise ConfigError(f"{path}: location {loc.name!r} has out-of-range coordinates")
        locations.append(loc)
    return locations
