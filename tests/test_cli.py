"""CLI surface: check / run / ask, exercised through main()."""

import json

import pytest

from heatline.cli import main

REAL_FIXTURE = "tests/fixtures/jamaica_live.json"
EVENT_FIXTURE = "examples/illustrative_heat_event.json"


def test_check_command_succeeds(capsys):
    assert main(["check"]) == 0
    assert "Jamaica config valid" in capsys.readouterr().out


def test_run_command_with_real_fixture(tmp_path, capsys):
    code = main([
        "run", "--fixture", REAL_FIXTURE, "--channels", "console",
        "--state", str(tmp_path / "s.json"), "--bulletins", str(tmp_path / "b"),
        "--roster", str(tmp_path / "r.jsonl"), "--now", "2026-06-13T06:00",
    ])
    assert code == 0
    assert "alert window(s) in outlook" in capsys.readouterr().out
    assert (tmp_path / "b" / "latest.md").exists()


def test_run_command_with_event_fixture_issues_alerts(tmp_path, capsys):
    code = main([
        "run", "--fixture", EVENT_FIXTURE, "--channels", "console,jsonl",
        "--state", str(tmp_path / "s.json"), "--bulletins", str(tmp_path / "b"),
        "--roster", str(tmp_path / "r.jsonl"), "--now", "2026-06-13T06:00",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "newly issued" in out
    bulletin = (tmp_path / "b" / "latest.md").read_text(encoding="utf-8")
    assert "EMERGENCY" in bulletin


def test_run_with_roster_records_delivery(tmp_path, capsys):
    roster = tmp_path / "r.jsonl"
    roster.write_text(
        json.dumps({"audience": "outdoor_worker", "channel": "whatsapp", "recipient": "+18765550100"}) + "\n",
        encoding="utf-8",
    )
    code = main([
        "run", "--fixture", EVENT_FIXTURE, "--channels", "console,whatsapp",
        "--state", str(tmp_path / "s.json"), "--bulletins", str(tmp_path / "b"),
        "--roster", str(roster), "--now", "2026-06-13T06:00",
    ])
    assert code == 0  # whatsapp runs in dry-run mode without credentials


def test_ask_unknown_location_errors(capsys):
    code = main(["ask", "--location", "Atlantis", "--fixture", REAL_FIXTURE, "is it hot?"])
    assert code == 2
    assert "unknown location" in capsys.readouterr().err


def test_ask_without_llm_reports_error(monkeypatch, capsys):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    code = main([
        "ask", "--location", "Kingston", "--fixture", REAL_FIXTURE,
        "--now", "2026-06-13T06:00", "Is tomorrow safe for outdoor work?",
    ])
    assert code == 2
    assert "error" in capsys.readouterr().err.lower()


def test_bad_config_path_errors(capsys):
    code = main(["--config", "config/does_not_exist.yaml", "check"])
    assert code == 2
