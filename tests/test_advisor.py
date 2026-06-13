"""Two-way advisor: outlook summarisation (offline) and the no-LLM guard."""

from datetime import datetime

import pytest

from heatline.advisor import answer_question, summarise_outlook
from heatline.compose import load_playbooks
from heatline.config import load_config
from heatline.forecast import parse_hourly
from heatline.llm import LLMError

NOW = datetime(2026, 6, 13, 6, 0)


def _kingston(payload_builder):
    config = load_config("config/jamaica.yaml")
    location = next(l for l in config.locations if l.name == "Kingston")
    payload = payload_builder(NOW, {0: {h: (39.0, 65.0) for h in range(11, 16)}})
    return config, location, parse_hourly(payload)


def test_summarise_outlook_is_factual(payload_builder):
    config, location, readings = _kingston(payload_builder)
    summary = summarise_outlook(location, readings, config, NOW)
    assert "Kingston" in summary
    assert "heat index" in summary.lower()


def test_answer_question_requires_llm(monkeypatch, payload_builder):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    config, location, readings = _kingston(payload_builder)
    playbooks = load_playbooks("playbooks")
    with pytest.raises(LLMError):
        answer_question("Is tomorrow safe for the market?", location, readings, config, playbooks, NOW)
