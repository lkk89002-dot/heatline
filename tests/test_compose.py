"""Message composition, playbook loading and validation."""

from datetime import datetime, timedelta

import pytest

from heatline.alerts import AlertWindow
from heatline.compose import (
    PlaybookError,
    compose_for_window,
    human_date,
    load_playbooks,
    template_context,
    validate_playbooks,
)
from heatline.config import load_config


def _window(level="warning"):
    start = datetime(2026, 6, 13, 11)
    return AlertWindow("Kingston", level, "2026-06-13", start, start + timedelta(hours=3), 43.0, start.replace(hour=14), 4)


def test_playbooks_load_and_validate(playbooks_dir, jamaica_config):
    config = load_config(jamaica_config)
    playbooks = load_playbooks(playbooks_dir)
    assert {p.audience for p in playbooks} >= {
        "outdoor_worker", "elderly_caregiver", "chronic_illness",
        "community_health_aide", "general_public",
    }
    validate_playbooks(playbooks, config)  # must not raise


def test_template_context_keys(jamaica_config):
    config = load_config(jamaica_config)
    ctx = template_context(_window(), config)
    assert ctx["location"] == "Kingston"
    assert ctx["level"] == "WARNING"
    assert ctx["peak_hi"] == "43"
    assert ctx["ambulance"] == "110"  # Ambulance/Fire number from config


def test_compose_renders_every_audience(playbooks_dir, jamaica_config):
    config = load_config(jamaica_config)
    playbooks = load_playbooks(playbooks_dir)
    messages = compose_for_window(_window("emergency"), playbooks, config, use_llm=False)
    assert len(messages) == len(playbooks)
    for message in messages:
        assert "110" in message.text  # emergency number rendered
        assert "Kingston" in message.text
        assert message.generator == "template"


def test_voice_script_present_only_where_configured(playbooks_dir, jamaica_config):
    config = load_config(jamaica_config)
    playbooks = load_playbooks(playbooks_dir)
    messages = compose_for_window(_window("warning"), playbooks, config, use_llm=False)
    by_audience = {m.audience: m for m in messages}
    assert by_audience["general_public"].voice_script is not None
    assert by_audience["outdoor_worker"].voice_script is None


def test_validate_playbooks_detects_bad_placeholder(tmp_path, jamaica_config):
    config = load_config(jamaica_config)
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "audience: x\ndisplay_name: X\nsources: [s]\nprotective_actions: [a]\n"
        "messages:\n  watch: 'uses {nonexistent}'\n  warning: ok\n  emergency: ok\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaybookError):
        validate_playbooks(load_playbooks(tmp_path), config)


def test_human_date_is_readable():
    assert human_date("2026-06-13") == "Saturday 13 June"


def test_load_playbooks_empty_dir_raises(tmp_path):
    with pytest.raises(PlaybookError):
        load_playbooks(tmp_path)
