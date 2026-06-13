"""Orchestrator: one run of the Heatline pipeline.

    forecast → heat index → detect alert windows → frequency cap →
    compose audience messages → deliver to channels → write bulletin → save state

Every step is its own module; this file only wires them together and is the
single place that touches the network, the clock and the filesystem.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from . import bulletin as bulletin_mod
from .alerts import AlertWindow, apply_frequency_cap, detect_windows, prune_state
from .channels import DeliveryResult, build_channels
from .compose import (
    OutboundMessage,
    Playbook,
    compose_for_window,
    load_playbooks,
    validate_playbooks,
)
from .config import CountryConfig, load_config
from .forecast import fetch_hourly, parse_hourly
from .roster import Subscriber, load_roster
from .state import load_state, save_state

log = logging.getLogger("heatline.run")

DEFAULT_ALERT_HORIZON_HOURS = 48


@dataclass
class RunResult:
    windows: List[AlertWindow]
    sent_windows: List[AlertWindow]
    messages: List[OutboundMessage]
    deliveries: List[DeliveryResult]
    bulletin_path: Optional[Path]

    def summary(self) -> str:
        ok = sum(1 for d in self.deliveries if d.ok)
        return (
            f"{len(self.windows)} alert window(s) in outlook, "
            f"{len(self.sent_windows)} newly issued, "
            f"{len(self.messages)} message(s) composed, "
            f"{ok}/{len(self.deliveries)} deliveries ok"
        )


def run_pipeline(
    config_path,
    now: datetime,
    *,
    fixtures: Optional[Dict[str, dict]] = None,
    use_llm: bool = False,
    channels: Optional[List[str]] = None,
    state_path="state.json",
    bulletin_dir="bulletins",
    roster_path="roster.jsonl",
    outbox_path="bulletins/outbox.jsonl",
    prompts_dir="prompts",
    playbooks_dir="playbooks",
    alert_horizon_hours: int = DEFAULT_ALERT_HORIZON_HOURS,
) -> RunResult:
    config = load_config(config_path)
    playbooks = load_playbooks(playbooks_dir)
    validate_playbooks(playbooks, config)

    channel_names = channels if channels is not None else config.channels
    channel_map = build_channels(channel_names, jsonl_path=outbox_path)
    roster = load_roster(roster_path)

    all_windows = _detect_all(config, fixtures)

    horizon = now + timedelta(hours=alert_horizon_hours)
    upcoming = [w for w in all_windows if w.end + timedelta(hours=1) >= now and w.start <= horizon]

    state = load_state(state_path)
    to_send, new_state = apply_frequency_cap(upcoming, state, config.levels)

    messages = _compose_all(to_send, playbooks, config, prompts_dir, use_llm)
    deliveries = _deliver(messages, channel_map, roster, channel_names)

    bulletin_path = bulletin_mod.write_bulletin(bulletin_dir, config, all_windows, messages, now)

    save_state(state_path, prune_state(new_state, now.date().isoformat()))

    return RunResult(all_windows, to_send, messages, deliveries, bulletin_path)


def _detect_all(config: CountryConfig, fixtures: Optional[Dict[str, dict]]) -> List[AlertWindow]:
    windows: List[AlertWindow] = []
    for location in config.locations:
        if fixtures is not None:
            payload = fixtures.get(location.name)
            if payload is None:
                log.warning("no fixture for location %s — skipping", location.name)
                continue
            readings = parse_hourly(payload)
        else:
            readings = fetch_hourly(
                location.lat, location.lon, config.forecast_days, config.timezone
            )
        windows.extend(detect_windows(location.name, readings, config))
    return windows


def _compose_all(
    windows: List[AlertWindow],
    playbooks: List[Playbook],
    config: CountryConfig,
    prompts_dir: str,
    use_llm: bool,
) -> List[OutboundMessage]:
    messages: List[OutboundMessage] = []
    for window in windows:
        messages.extend(
            compose_for_window(window, playbooks, config, prompts_dir=prompts_dir, use_llm=use_llm)
        )
    return messages


def _deliver(
    messages: List[OutboundMessage],
    channel_map: Dict[str, object],
    roster: List[Subscriber],
    channel_names: List[str],
) -> List[DeliveryResult]:
    """Route each message. Roster subscribers get their chosen channel; every
    message is also echoed to console/jsonl channels (operator visibility and
    the megaphone relay export) regardless of roster."""
    results: List[DeliveryResult] = []
    by_audience: Dict[str, List[Subscriber]] = {}
    for sub in roster:
        by_audience.setdefault(sub.audience, []).append(sub)

    broadcast = [name for name in channel_names if name in ("console", "jsonl")]

    for message in messages:
        for name in broadcast:
            results.append(channel_map[name].send(f"{message.audience}@{name}", message))
        for sub in by_audience.get(message.audience, []):
            channel = channel_map.get(sub.channel)
            if channel is None:
                results.append(
                    DeliveryResult(sub.channel, sub.recipient, ok=False, detail="channel not enabled")
                )
                continue
            if sub.channel in broadcast:
                continue  # already echoed above
            results.append(channel.send(sub.recipient, message))
    return results


def load_fixture_map(path) -> Dict[str, dict]:
    """Load a JSON file mapping location name -> Open-Meteo response payload."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: fixture must be an object mapping location name -> payload")
    return data
