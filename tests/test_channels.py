"""Channel adapters: registry, console, jsonl and dry-run network channels."""

import json

import pytest

from heatline.channels import available_channels, build_channels
from heatline.channels.whatsapp import WhatsAppChannel
from heatline.compose import OutboundMessage


def _message():
    return OutboundMessage(
        audience="general_public", location="Kingston", level="warning",
        date="2026-06-13", text="Stay cool. Call 110 in an emergency.",
        voice_script=None, generator="template",
    )


def test_registry_lists_all_channels():
    assert set(available_channels()) == {"console", "jsonl", "whatsapp", "messenger", "sms"}


def test_build_unknown_channel_raises():
    with pytest.raises(ValueError):
        build_channels(["telepathy"])


def test_console_channel_reports_success(capsys):
    channels = build_channels(["console"])
    result = channels["console"].send("general_public@console", _message())
    assert result.ok
    assert "Kingston" in capsys.readouterr().out


def test_jsonl_channel_appends_records(tmp_path):
    path = tmp_path / "out.jsonl"
    channels = build_channels(["jsonl"], jsonl_path=str(path))
    channels["jsonl"].send("aide-1", _message())
    channels["jsonl"].send("aide-2", _message())
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    record = json.loads(lines[0])
    assert record["recipient"] == "aide-1"
    assert record["location"] == "Kingston"


def test_whatsapp_dry_run_without_credentials(monkeypatch):
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    channel = WhatsAppChannel()
    assert not channel.configured
    result = channel.send("+18765550100", _message())
    assert result.ok
    assert "dry-run" in result.detail


def test_send_never_raises_on_each_channel():
    msg = _message()
    for name in available_channels():
        channel = build_channels([name], jsonl_path="/tmp/heatline_test_outbox.jsonl")[name]
        result = channel.send("recipient", msg)
        assert result.channel == name
        assert isinstance(result.ok, bool)
