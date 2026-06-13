"""Country config loading and validation."""

import pytest

from heatline.config import ConfigError, load_config


def test_load_jamaica_config(jamaica_config):
    config = load_config(jamaica_config)
    assert config.country == "Jamaica"
    assert config.timezone == "America/Jamaica"
    assert len(config.locations) == 6
    # levels are sorted most-severe (highest threshold) first
    assert [level.name for level in config.levels] == ["emergency", "warning", "watch"]
    assert config.emergency["Police"] == "119"


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_threshold_out_of_range_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "country: Test\ntimezone: UTC\nlanguage: English\n"
        "emergency: {Ambulance: '110'}\n"
        "alert_levels:\n  - {name: watch, hi_c: 99}\n"
        "locations:\n  - {name: X, lat: 0, lon: 0}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_duplicate_level_names_rejected(tmp_path):
    bad = tmp_path / "dup.yaml"
    bad.write_text(
        "country: Test\ntimezone: UTC\nlanguage: English\n"
        "emergency: {Ambulance: '110'}\n"
        "alert_levels:\n  - {name: watch, hi_c: 38}\n  - {name: watch, hi_c: 41}\n"
        "locations:\n  - {name: X, lat: 0, lon: 0}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_out_of_range_coordinates_rejected(tmp_path):
    bad = tmp_path / "geo.yaml"
    bad.write_text(
        "country: Test\ntimezone: UTC\nlanguage: English\n"
        "emergency: {Ambulance: '110'}\n"
        "alert_levels:\n  - {name: watch, hi_c: 38}\n"
        "locations:\n  - {name: X, lat: 999, lon: 0}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)
