"""End-to-end pipeline run, offline via fixtures (no network, no LLM)."""

from datetime import datetime

import pytest

from heatline.run import run_pipeline

NOW = datetime(2026, 6, 13, 6, 0)
LOCATIONS = ["Kingston", "Spanish Town", "Montego Bay", "May Pen", "Savanna-la-Mar", "Mandeville"]


@pytest.fixture
def fixtures(payload_builder):
    """Kingston has a dangerous hot day today; everywhere else is mild."""
    hot = {0: {h: (40.0, 65.0) for h in range(11, 16)}}
    mild = {0: {h: (30.0, 60.0) for h in range(11, 16)}}
    return {name: payload_builder(NOW, hot if name == "Kingston" else mild) for name in LOCATIONS}


def _run(tmp_path, fixtures, **kw):
    return run_pipeline(
        "config/jamaica.yaml",
        NOW,
        fixtures=fixtures,
        state_path=str(tmp_path / "state.json"),
        bulletin_dir=str(tmp_path / "bulletins"),
        roster_path=str(tmp_path / "roster.jsonl"),
        outbox_path=str(tmp_path / "bulletins" / "outbox.jsonl"),
        **kw,
    )


def test_pipeline_detects_and_composes(tmp_path, fixtures):
    result = _run(tmp_path, fixtures)
    assert any(w.location == "Kingston" and w.level == "emergency" for w in result.windows)
    assert len(result.sent_windows) == 1
    # one message per playbook for the single newly-issued window
    assert len(result.messages) == 5
    assert result.messages and all(d.ok for d in result.deliveries)


def test_pipeline_writes_bulletin(tmp_path, fixtures):
    result = _run(tmp_path, fixtures)
    assert result.bulletin_path.exists()
    text = result.bulletin_path.read_text(encoding="utf-8")
    assert "Kingston" in text and "EMERGENCY" in text
    assert (tmp_path / "bulletins" / "archive" / "2026-06-13.md").exists()


def test_pipeline_writes_jsonl_outbox(tmp_path, fixtures):
    _run(tmp_path, fixtures)
    outbox = tmp_path / "bulletins" / "outbox.jsonl"
    assert outbox.exists()
    assert len(outbox.read_text(encoding="utf-8").strip().splitlines()) == 5


def test_frequency_cap_suppresses_second_run(tmp_path, fixtures):
    first = _run(tmp_path, fixtures)
    assert len(first.messages) == 5
    second = _run(tmp_path, fixtures)  # same state file → already alerted
    assert second.messages == []
    assert second.sent_windows == []
    # the 7-day outlook still shows the window even when no new message is sent
    assert any(w.location == "Kingston" for w in second.windows)


def test_calm_everywhere_sends_nothing(tmp_path, payload_builder):
    calm = {name: payload_builder(NOW, {0: {13: (29.0, 60.0)}}) for name in LOCATIONS}
    result = _run(tmp_path, calm)
    assert result.windows == []
    assert result.messages == []
    assert result.bulletin_path.exists()  # a no-alert bulletin is still published
