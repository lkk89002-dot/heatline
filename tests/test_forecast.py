"""Forecast parsing and validation."""

from datetime import datetime

import pytest

from heatline.forecast import ForecastError, parse_hourly


def test_parse_hourly_computes_heat_index(payload_builder):
    payload = payload_builder(datetime(2026, 6, 13, 0), {0: {12: (35.0, 60.0)}}, days=1)
    readings = parse_hourly(payload)
    assert len(readings) == 24
    noon = next(r for r in readings if r.time.hour == 12)
    assert noon.temp_c == 35.0
    assert noon.heat_index_c > 35.0  # humid heat feels hotter than the air temp


def test_parse_hourly_skips_null_hours(payload_builder):
    payload = payload_builder(datetime(2026, 6, 13, 0), {}, days=1)
    payload["hourly"]["temperature_2m"][5] = None
    readings = parse_hourly(payload)
    assert len(readings) == 23
    assert all(r.time.hour != 5 for r in readings)


def test_parse_hourly_rejects_missing_block():
    with pytest.raises(ForecastError):
        parse_hourly({"daily": {}})


def test_parse_hourly_rejects_mismatched_lengths():
    payload = {"hourly": {"time": ["2026-06-13T00:00"], "temperature_2m": [], "relative_humidity_2m": [], "apparent_temperature": []}}
    with pytest.raises(ForecastError):
        parse_hourly(payload)


def test_parse_hourly_rejects_all_null():
    payload = {"hourly": {"time": ["2026-06-13T00:00"], "temperature_2m": [None], "relative_humidity_2m": [None], "apparent_temperature": [None]}}
    with pytest.raises(ForecastError):
        parse_hourly(payload)
