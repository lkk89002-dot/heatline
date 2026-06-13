"""Open-Meteo forecast client.

Open-Meteo (https://open-meteo.com) is free for non-commercial use, requires
no API key, and serves forecasts for any coordinates — which is what makes
Heatline deployable in any country with a one-file configuration change.
Weather data by Open-Meteo.com (CC-BY 4.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

from .heat_index import heat_index_c

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_FIELDS = "temperature_2m,relative_humidity_2m,apparent_temperature"
REQUEST_TIMEOUT_S = 30


class ForecastError(RuntimeError):
    """Raised when the forecast provider is unreachable or returns bad data."""


@dataclass(frozen=True)
class HourlyReading:
    time: datetime  # local time at the forecast location (naive)
    temp_c: float
    humidity_pct: float
    apparent_c: float
    heat_index_c: float


def fetch_hourly(
    lat: float,
    lon: float,
    days: int,
    timezone: str,
    session: Optional[requests.Session] = None,
) -> List[HourlyReading]:
    """Fetch an hourly forecast and compute the heat index for every hour."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY_FIELDS,
        "forecast_days": days,
        "timezone": timezone,
    }
    http = session or requests
    try:
        resp = http.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:  # pragma: no cover - network
        raise ForecastError(f"Open-Meteo request failed for ({lat}, {lon}): {exc}") from exc
    except ValueError as exc:  # pragma: no cover - network
        raise ForecastError(f"Open-Meteo returned non-JSON for ({lat}, {lon})") from exc
    return parse_hourly(payload)


def parse_hourly(payload: dict) -> List[HourlyReading]:
    """Validate and convert an Open-Meteo response into hourly readings."""
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise ForecastError("Open-Meteo response is missing the 'hourly' block")
    try:
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        hums = hourly["relative_humidity_2m"]
        feels = hourly["apparent_temperature"]
    except KeyError as exc:
        raise ForecastError(f"Open-Meteo response is missing hourly field {exc}") from exc
    if not (len(times) == len(temps) == len(hums) == len(feels)):
        raise ForecastError("Open-Meteo hourly arrays have mismatched lengths")

    readings = []
    for time_str, temp, hum, feel in zip(times, temps, hums, feels):
        if temp is None or hum is None:
            continue  # provider gap: skip the hour rather than invent values
        temp_f = float(temp)
        hum_f = max(0.0, min(100.0, float(hum)))
        readings.append(
            HourlyReading(
                time=datetime.fromisoformat(time_str),
                temp_c=temp_f,
                humidity_pct=hum_f,
                apparent_c=float(feel) if feel is not None else temp_f,
                heat_index_c=round(heat_index_c(temp_f, hum_f), 1),
            )
        )
    if not readings:
        raise ForecastError("Open-Meteo returned no usable hourly readings")
    return readings
