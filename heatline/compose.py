"""Turn one alert window into audience-specific messages.

Two modes:
- template: render the playbook message for the alert level. Always available
  — no API key, no network call, content exactly as reviewed.
- llm: rewrite the playbook template for the audience with an AI backend,
  constrained to the playbook facts. Falls back to the template on any error:
  personalization is optional, delivery is not (do-no-harm).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import llm
from .alerts import AlertWindow
from .config import CountryConfig

log = logging.getLogger("heatline.compose")

DEFAULT_PROMPT_FILE = "alert_message.md"


class PlaybookError(ValueError):
    """Raised when playbook content is missing or inconsistent with config."""


@dataclass(frozen=True)
class Playbook:
    audience: str
    display_name: str
    sources: List[str]
    key_risks: List[str]
    protective_actions: List[str]
    warning_signs: List[str]
    messages: Dict[str, str]  # alert level name -> message template
    voice: bool


@dataclass(frozen=True)
class OutboundMessage:
    audience: str
    location: str
    level: str
    date: str
    text: str
    voice_script: Optional[str]
    generator: str  # "template" or "llm:<provider>"


def load_playbooks(directory) -> List[Playbook]:
    directory = Path(directory)
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise PlaybookError(f"no playbooks (*.yaml) found in {directory}")
    return [_load_one(path) for path in files]


def _load_one(path: Path) -> Playbook:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlaybookError(f"{path}: invalid YAML: {exc}")
    if not isinstance(raw, dict):
        raise PlaybookError(f"{path}: playbook root must be a mapping")
    missing = [k for k in ("audience", "display_name", "sources", "protective_actions", "messages") if k not in raw]
    if missing:
        raise PlaybookError(f"{path}: missing required key(s): {', '.join(missing)}")
    messages = {str(k).strip().lower(): str(v) for k, v in dict(raw["messages"]).items()}
    return Playbook(
        audience=str(raw["audience"]).strip(),
        display_name=str(raw["display_name"]).strip(),
        sources=[str(s) for s in raw["sources"]],
        key_risks=[str(s) for s in raw.get("key_risks", [])],
        protective_actions=[str(s) for s in raw["protective_actions"]],
        warning_signs=[str(s) for s in raw.get("warning_signs", [])],
        messages=messages,
        voice=bool(raw.get("voice", False)),
    )


def validate_playbooks(playbooks: List[Playbook], config: CountryConfig) -> None:
    """Fail fast at startup if content and config disagree."""
    dummy = {key: "x" for key in _CONTEXT_KEYS}
    problems = []
    for playbook in playbooks:
        for level in config.levels:
            template = playbook.messages.get(level.name)
            if template is None:
                problems.append(f"{playbook.audience}: no message for level {level.name!r}")
                continue
            try:
                template.format(**dummy)
            except KeyError as exc:
                problems.append(f"{playbook.audience}/{level.name}: unknown placeholder {exc}")
            except (IndexError, ValueError) as exc:
                problems.append(f"{playbook.audience}/{level.name}: bad template: {exc}")
    if problems:
        raise PlaybookError("playbook validation failed:\n  - " + "\n  - ".join(problems))


_CONTEXT_KEYS = ("location", "level", "date", "peak_hi", "window", "ambulance", "country")


def template_context(window: AlertWindow, config: CountryConfig) -> Dict[str, str]:
    return {
        "location": window.location,
        "level": window.level.upper(),
        "date": human_date(window.date),
        "peak_hi": f"{window.peak_hi_c:.0f}",
        "window": f"{hour_label(window.start)} and {hour_label(window.end + timedelta(hours=1))}",
        "ambulance": ambulance_number(config),
        "country": config.country,
    }


def ambulance_number(config: CountryConfig) -> str:
    """The number to call for a medical emergency: the first emergency service
    whose name mentions an ambulance, else the first listed number."""
    for service, number in config.emergency.items():
        if "ambulance" in service.lower():
            return number
    return next(iter(config.emergency.values()))


def compose_for_window(
    window: AlertWindow,
    playbooks: List[Playbook],
    config: CountryConfig,
    prompts_dir="prompts",
    use_llm: bool = False,
) -> List[OutboundMessage]:
    context = template_context(window, config)
    out = []
    for playbook in playbooks:
        base = playbook.messages[window.level].format(**context).strip()
        text, generator = base, "template"
        if use_llm:
            try:
                text = _llm_rewrite(playbook, window, config, Path(prompts_dir), context, base)
                generator = "llm:" + llm.active_provider()
            except llm.LLMError as exc:
                log.warning(
                    "LLM personalization failed for %s/%s — using reviewed template (%s)",
                    window.location, playbook.audience, exc,
                )
        out.append(
            OutboundMessage(
                audience=playbook.audience,
                location=window.location,
                level=window.level,
                date=window.date,
                text=text,
                voice_script=_voice_script_from(text) if playbook.voice else None,
                generator=generator,
            )
        )
    return out


def _llm_rewrite(
    playbook: Playbook,
    window: AlertWindow,
    config: CountryConfig,
    prompts_dir: Path,
    context: Dict[str, str],
    base: str,
) -> str:
    prompt_template = load_prompt(prompts_dir, playbook.audience)
    prompt_context = dict(context)
    prompt_context.update(
        {
            "audience": playbook.audience,
            "display_name": playbook.display_name,
            "language": config.language,
            "protective_actions": "\n".join("- " + a for a in playbook.protective_actions),
            "warning_signs": "\n".join("- " + s for s in playbook.warning_signs),
            "base_message": base,
        }
    )
    system = prompt_template.format_map(_SafeDict(prompt_context))
    return llm.generate(system, "Write the final message now. Output only the message text.")


def load_prompt(prompts_dir: Path, audience: str) -> str:
    """Audience-specific prompt (prompts/<audience>.md) or the default."""
    prompts_dir = Path(prompts_dir)
    for candidate in (prompts_dir / f"{audience}.md", prompts_dir / DEFAULT_PROMPT_FILE):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise PlaybookError(f"no prompt template found in {prompts_dir} (expected {DEFAULT_PROMPT_FILE})")


class _SafeDict(dict):
    """format_map helper: leave unknown placeholders intact instead of crashing."""

    def __missing__(self, key):
        return "{" + key + "}"


def _voice_script_from(text: str) -> str:
    """Flatten a message into a script suitable for reading aloud / TTS."""
    flat = text.replace("**", "").replace("•", "")
    lines = [line.strip().lstrip("-• ").strip() for line in flat.splitlines()]
    sentences = [line if line.endswith((".", "!", "?", ":")) else line + "." for line in lines if line]
    return " ".join(" ".join(sentences).split())


def human_date(date_iso: str) -> str:
    d = date.fromisoformat(date_iso)
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')}"


def hour_label(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return f"{hour}{'am' if moment.hour < 12 else 'pm'}"
