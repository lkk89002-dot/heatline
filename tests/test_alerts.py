"""Alert-window detection and the do-no-harm frequency cap.

These tests build HourlyReading objects with explicit heat-index values so the
alert *logic* is verified independently of the heat-index formula (covered in
test_heat_index.py)."""

from datetime import datetime, timedelta
from typing import Dict

from heatline.alerts import (
    AlertWindow,
    apply_frequency_cap,
    detect_windows,
    prune_state,
)
from heatline.config import load_config
from heatline.forecast import HourlyReading


def _day(date: datetime, hourly_hi: Dict[int, float]) -> list:
    readings = []
    for hour in range(24):
        hi = hourly_hi.get(hour, 28.0)
        moment = date.replace(hour=hour, minute=0, second=0, microsecond=0)
        readings.append(HourlyReading(moment, 30.0, 60.0, 30.0, hi))
    return readings


def _levels():
    return load_config("config/jamaica.yaml").levels


def _config():
    return load_config("config/jamaica.yaml")


def test_detects_emergency_as_most_severe():
    readings = _day(datetime(2026, 6, 13), {12: 46.0, 13: 46.0, 14: 46.0})
    windows = detect_windows("Kingston", readings, _config())
    assert len(windows) == 1
    assert windows[0].level == "emergency"
    assert windows[0].hours == 3
    assert windows[0].peak_hi_c == 46.0


def test_detects_warning_below_emergency():
    readings = _day(datetime(2026, 6, 13), {12: 42.0, 13: 42.0, 14: 42.0})
    windows = detect_windows("Kingston", readings, _config())
    assert windows[0].level == "warning"


def test_detects_watch_with_minimum_duration():
    readings = _day(datetime(2026, 6, 13), {10: 39.0, 11: 39.0, 12: 39.0, 13: 39.0})
    windows = detect_windows("Kingston", readings, _config())
    assert windows[0].level == "watch"
    assert windows[0].hours == 4


def test_watch_not_triggered_below_minimum_duration():
    # watch requires 3 consecutive hours; only 2 here.
    readings = _day(datetime(2026, 6, 13), {12: 39.0, 13: 39.0})
    assert detect_windows("Kingston", readings, _config()) == []


def test_non_consecutive_hours_do_not_count():
    # 4 hot hours but a gap at 12 breaks the run into 2 + 2, below the 3h minimum.
    readings = _day(datetime(2026, 6, 13), {10: 39.0, 11: 39.0, 13: 39.0, 14: 39.0})
    assert detect_windows("Kingston", readings, _config()) == []


def test_calm_day_produces_no_window():
    readings = _day(datetime(2026, 6, 13), {12: 30.0, 13: 30.0, 14: 31.0})
    assert detect_windows("Kingston", readings, _config()) == []


def test_nighttime_heat_ignored():
    # Hour 3 is outside the 08–18 daytime window.
    readings = _day(datetime(2026, 6, 13), {3: 50.0})
    assert detect_windows("Kingston", readings, _config()) == []


def _window(level: str, location: str = "Kingston", date: str = "2026-06-13") -> AlertWindow:
    start = datetime.fromisoformat(date + "T11:00")
    return AlertWindow(location, level, date, start, start + timedelta(hours=2), 46.0, start, 3)


def test_frequency_cap_sends_then_suppresses():
    levels = _levels()
    windows = [_window("warning")]
    to_send, state = apply_frequency_cap(windows, {}, levels)
    assert len(to_send) == 1
    # Same location/day/level on the next run: suppressed.
    again, _ = apply_frequency_cap(windows, state, levels)
    assert again == []


def test_frequency_cap_allows_escalation():
    levels = _levels()
    _, state = apply_frequency_cap([_window("watch")], {}, levels)
    to_send, _ = apply_frequency_cap([_window("emergency")], state, levels)
    assert len(to_send) == 1
    assert to_send[0].level == "emergency"


def test_frequency_cap_does_not_downgrade():
    levels = _levels()
    _, state = apply_frequency_cap([_window("emergency")], {}, levels)
    to_send, _ = apply_frequency_cap([_window("watch")], state, levels)
    assert to_send == []


def test_prune_state_drops_old_entries():
    state = {"2026-06-01|Kingston": "watch", "2026-06-13|Kingston": "warning"}
    pruned = prune_state(state, "2026-06-13", keep_days=7)
    assert "2026-06-13|Kingston" in pruned
    assert "2026-06-01|Kingston" not in pruned
