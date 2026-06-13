"""Shared test fixtures and an Open-Meteo payload builder."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def jamaica_config() -> Path:
    return REPO_ROOT / "config" / "jamaica.yaml"


@pytest.fixture
def playbooks_dir() -> Path:
    return REPO_ROOT / "playbooks"


@pytest.fixture
def prompts_dir() -> Path:
    return REPO_ROOT / "prompts"


def open_meteo_payload(
    start: datetime,
    day_profiles: Dict[int, Dict[int, Tuple[float, float]]],
    days: int = 7,
    base: Tuple[float, float] = (28.0, 65.0),
) -> dict:
    """Build a synthetic Open-Meteo hourly response.

    day_profiles maps a day index (0 = start's date) to {hour: (temp_c, rh)}.
    Unspecified hours use `base`. Mirrors the real API's hourly block shape.
    """
    times, temps, hums, feels = [], [], [], []
    start_date = start.date()
    for day_index in range(days):
        day = start_date + timedelta(days=day_index)
        profile = day_profiles.get(day_index, {})
        for hour in range(24):
            temp, rh = profile.get(hour, base)
            moment = datetime(day.year, day.month, day.day, hour)
            times.append(moment.isoformat(timespec="minutes"))
            temps.append(temp)
            hums.append(rh)
            feels.append(temp)
    return {
        "hourly": {
            "time": times,
            "temperature_2m": temps,
            "relative_humidity_2m": hums,
            "apparent_temperature": feels,
        }
    }


@pytest.fixture
def payload_builder():
    return open_meteo_payload
