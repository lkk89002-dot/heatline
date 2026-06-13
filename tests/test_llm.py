"""LLM provider resolution and the do-no-harm fallback to templates."""

from datetime import datetime, timedelta

import pytest

from heatline import llm
from heatline.alerts import AlertWindow
from heatline.compose import compose_for_window, load_playbooks
from heatline.config import load_config


def test_active_provider_explicit_none(monkeypatch):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    assert llm.active_provider() == "none"


def test_active_provider_autodetects_from_keys(monkeypatch):
    monkeypatch.delenv("HEATLINE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.active_provider() == "anthropic"


def test_active_provider_unknown_value_raises(monkeypatch):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "wizard")
    with pytest.raises(llm.LLMError):
        llm.active_provider()


def test_forced_provider_without_key_raises(monkeypatch):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMError):
        llm.active_provider()


def test_compose_falls_back_to_template_when_no_llm(monkeypatch):
    # use_llm=True but no provider configured: delivery must still happen, using
    # the reviewed template — personalization is optional, alerting is not.
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    config = load_config("config/jamaica.yaml")
    playbooks = load_playbooks("playbooks")
    start = datetime(2026, 6, 13, 11)
    window = AlertWindow("Kingston", "warning", "2026-06-13", start, start + timedelta(hours=3), 43.0, start, 4)
    messages = compose_for_window(window, playbooks, config, use_llm=True)
    assert len(messages) == len(playbooks)
    assert all(m.generator == "template" for m in messages)
    assert all("110" in m.text for m in messages)
