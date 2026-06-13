"""Detect heat-stress alert windows and enforce do-no-harm frequency caps.

Design choices (see docs/architecture.md):
- An alert window is the most severe level whose heat-index threshold holds for
  its minimum number of *consecutive daytime hours* — single hot spikes do not
  page anyone unless the level allows it (emergency does).
- At most one alert per location per local day; a repeat is sent only when the
  level escalates. Alert fatigue is a documented failure mode of warning
  systems (WMO/WHO heatwave guidance), so the cap is a core feature, not an
  afterthought.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .config import AlertLevel, CountryConfig
from .forecast import HourlyReading


@dataclass(frozen=True)
class AlertWindow:
    location: str
    level: str
    date: str  # YYYY-MM-DD, local
    start: datetime
    end: datetime  # start of the last qualifying hour
    peak_hi_c: float
    peak_time: datetime
    hours: int


def detect_windows(
    location_name: str, readings: List[HourlyReading], config: CountryConfig
) -> List[AlertWindow]:
    """Return at most one alert window per local day for one location."""
    by_day: Dict[str, List[HourlyReading]] = defaultdict(list)
    for reading in readings:
        if config.day_start_hour <= reading.time.hour <= config.day_end_hour:
            by_day[reading.time.date().isoformat()].append(reading)

    windows = []
    for day, day_readings in sorted(by_day.items()):
        window = _best_window_for_day(location_name, day, day_readings, config.levels)
        if window is not None:
            windows.append(window)
    return windows


def _best_window_for_day(
    location: str, day: str, readings: List[HourlyReading], levels: List[AlertLevel]
) -> Optional[AlertWindow]:
    for level in levels:  # most severe first
        run = _longest_consecutive_run(readings, level.hi_c)
        if len(run) >= level.min_consecutive_hours:
            peak = max(run, key=lambda r: r.heat_index_c)
            return AlertWindow(
                location=location,
                level=level.name,
                date=day,
                start=run[0].time,
                end=run[-1].time,
                peak_hi_c=peak.heat_index_c,
                peak_time=peak.time,
                hours=len(run),
            )
    return None


def _longest_consecutive_run(readings: List[HourlyReading], threshold: float) -> List[HourlyReading]:
    """Longest run of hourly readings >= threshold with no missing hours."""
    best: List[HourlyReading] = []
    current: List[HourlyReading] = []
    for reading in readings:
        contiguous = not current or (reading.time - current[-1].time) == timedelta(hours=1)
        if reading.heat_index_c >= threshold and contiguous:
            current = current + [reading]
        elif reading.heat_index_c >= threshold:
            current = [reading]
        else:
            current = []
        if len(current) > len(best):
            best = current
    return best


def apply_frequency_cap(
    windows: List[AlertWindow], state: Dict[str, str], levels: List[AlertLevel]
) -> Tuple[List[AlertWindow], Dict[str, str]]:
    """Suppress repeat alerts for the same location and day.

    Returns the windows to send and a *new* state mapping
    ("YYYY-MM-DD|location" -> level already alerted). A repeat is allowed only
    when the new window is more severe than what was already sent.
    """
    rank = {level.name: i for i, level in enumerate(levels)}  # 0 = most severe
    new_state = dict(state)
    to_send = []
    for window in windows:
        key = f"{window.date}|{window.location}"
        previous = new_state.get(key)
        if previous is not None and rank.get(window.level, 99) >= rank.get(previous, 99):
            continue
        to_send.append(window)
        new_state[key] = window.level
    return to_send, new_state


def prune_state(state: Dict[str, str], today_iso: str, keep_days: int = 14) -> Dict[str, str]:
    """Drop state entries older than keep_days so the state file stays small."""
    cutoff = date.fromisoformat(today_iso) - timedelta(days=keep_days)
    pruned = {}
    for key, level in state.items():
        try:
            entry_date = date.fromisoformat(key.split("|", 1)[0])
        except (ValueError, IndexError):
            continue  # unparseable entries are dropped
        if entry_date >= cutoff:
            pruned[key] = level
    return pruned
