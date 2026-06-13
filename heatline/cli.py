"""Command-line interface: `heatline run | ask | check`."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import llm
from .advisor import answer_question
from .channels import available_channels
from .compose import load_playbooks, validate_playbooks
from .config import ConfigError, load_config
from .forecast import ForecastError, fetch_hourly, parse_hourly
from .run import load_fixture_map, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="heatline", description="AI heat-health early warning and advisory.")
    parser.add_argument("--config", default="config/jamaica.yaml", help="country config file")
    parser.add_argument("--playbooks", default="playbooks", help="playbooks directory")
    parser.add_argument("--prompts", default="prompts", help="prompt templates directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one alert pipeline pass")
    run.add_argument("--fixture", help="offline Open-Meteo fixture JSON (no network)")
    run.add_argument("--llm", action="store_true", help="personalise messages with an LLM backend")
    run.add_argument("--channels", help=f"comma-separated; available: {', '.join(available_channels())}")
    run.add_argument("--state", default="state.json", help="frequency-cap state file")
    run.add_argument("--bulletins", default="bulletins", help="bulletin output directory")
    run.add_argument("--roster", default="roster.jsonl", help="opt-in subscriber roster (optional)")
    run.add_argument("--now", help="override current time (ISO 8601), for testing/replay")

    ask = sub.add_parser("ask", help="answer a resident question, grounded in the forecast")
    ask.add_argument("--location", required=True, help="location name from the config")
    ask.add_argument("--fixture", help="offline Open-Meteo fixture JSON (no network)")
    ask.add_argument("--now", help="override current time (ISO 8601)")
    ask.add_argument("question", help="the question to answer")

    sub.add_parser("check", help="validate config and playbooks, no network")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "check":
            return _cmd_check(args)
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "ask":
            return _cmd_ask(args)
    except (ConfigError, ForecastError, llm.LLMError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def _now_from(value: Optional[str]) -> datetime:
    if value:
        return datetime.fromisoformat(value)
    return datetime.now()


def _cmd_check(args) -> int:
    config = load_config(args.config)
    playbooks = load_playbooks(args.playbooks)
    validate_playbooks(playbooks, config)
    print(f"OK: {config.country} config valid — {len(config.locations)} location(s), "
          f"{len(config.levels)} alert level(s), {len(playbooks)} playbook(s).")
    print(f"     channels: {', '.join(config.channels)} | language: {config.language} | "
          f"LLM backend: {llm.active_provider()}")
    return 0


def _cmd_run(args) -> int:
    fixtures = load_fixture_map(args.fixture) if args.fixture else None
    channels = [c.strip() for c in args.channels.split(",")] if args.channels else None
    result = run_pipeline(
        args.config,
        _now_from(args.now),
        fixtures=fixtures,
        use_llm=args.llm,
        channels=channels,
        state_path=args.state,
        bulletin_dir=args.bulletins,
        roster_path=args.roster,
        outbox_path=str(Path(args.bulletins) / "outbox.jsonl"),
        prompts_dir=args.prompts,
        playbooks_dir=args.playbooks,
    )
    print(result.summary())
    if result.bulletin_path:
        print(f"bulletin: {result.bulletin_path}")
    return 0


def _cmd_ask(args) -> int:
    config = load_config(args.config)
    playbooks = load_playbooks(args.playbooks)
    location = next((l for l in config.locations if l.name.lower() == args.location.lower()), None)
    if location is None:
        names = ", ".join(l.name for l in config.locations)
        print(f"error: unknown location {args.location!r}. Known: {names}", file=sys.stderr)
        return 2
    now = _now_from(args.now)
    if args.fixture:
        readings = parse_hourly(load_fixture_map(args.fixture)[location.name])
    else:
        readings = fetch_hourly(location.lat, location.lon, config.forecast_days, config.timezone)
    answer = answer_question(
        args.question, location, readings, config, playbooks, now, prompts_dir=args.prompts
    )
    print(answer)
    return 0
