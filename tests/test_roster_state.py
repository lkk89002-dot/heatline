"""Opt-in roster loading and frequency-cap state persistence."""

import pytest

from heatline.roster import RosterError, load_roster
from heatline.state import load_state, save_state


def test_missing_roster_is_empty(tmp_path):
    assert load_roster(tmp_path / "none.jsonl") == []


def test_roster_loads_valid_entries(tmp_path):
    path = tmp_path / "roster.jsonl"
    path.write_text(
        '# comment line ignored\n'
        '{"audience": "outdoor_worker", "channel": "whatsapp", "recipient": "+18765550100"}\n'
        '\n'
        '{"audience": "general_public", "channel": "sms", "recipient": "+18765550101"}\n',
        encoding="utf-8",
    )
    roster = load_roster(path)
    assert len(roster) == 2
    assert roster[0].audience == "outdoor_worker"
    assert roster[1].channel == "sms"


def test_roster_rejects_malformed_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"audience": "x", "channel": "whatsapp"}\n', encoding="utf-8")
    with pytest.raises(RosterError):
        load_roster(path)


def test_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, {"2026-06-13|Kingston": "warning"})
    assert load_state(path) == {"2026-06-13|Kingston": "warning"}


def test_corrupt_state_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_state(path) == {}
