"""Two-way advisory: answer a resident's question grounded in the forecast.

This is the half of Heatline a broadcast system cannot do — "My mother has
hypertension; is tomorrow safe for the market?". The answer is grounded in the
location's actual forecast and the reviewed playbook guidance, and the model
is instructed never to invent medical facts and to defer to emergency services
for red-flag symptoms (do-no-harm).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from . import llm
from .alerts import detect_windows
from .compose import Playbook, hour_label, human_date, load_prompt
from .config import CountryConfig, Location
from .forecast import HourlyReading

ADVISOR_PROMPT_FILE = "advisor.md"


def summarise_outlook(
    location: Location, readings: List[HourlyReading], config: CountryConfig, now: datetime
) -> str:
    """A compact, factual 3-day heat outlook string the model can quote."""
    horizon = now + timedelta(days=3)
    daytime = [
        r for r in readings
        if now <= r.time <= horizon and config.day_start_hour <= r.time.hour <= config.day_end_hour
    ]
    if not daytime:
        return f"No daytime forecast data available for {location.name} in the next 3 days."
    windows = detect_windows(location.name, readings, config)
    lines = [f"Location: {location.name}, {config.country}."]
    by_day = {}
    for reading in daytime:
        day = reading.time.date().isoformat()
        if day not in by_day or reading.heat_index_c > by_day[day].heat_index_c:
            by_day[day] = reading
    for day, peak in sorted(by_day.items()):
        lines.append(
            f"- {human_date(day)}: peak heat index ~{peak.heat_index_c:.0f} °C "
            f"around {hour_label(peak.time)} (air {peak.temp_c:.0f} °C, humidity {peak.humidity_pct:.0f}%)."
        )
    for window in windows:
        if now.date() <= datetime.fromisoformat(window.start.isoformat()).date() <= horizon.date():
            lines.append(
                f"- ALERT ({window.level.upper()}) on {human_date(window.date)}: heat index above "
                f"threshold for {window.hours} h, peaking ~{window.peak_hi_c:.0f} °C."
            )
    return "\n".join(lines)


def answer_question(
    question: str,
    location: Location,
    readings: List[HourlyReading],
    config: CountryConfig,
    playbooks: List[Playbook],
    now: datetime,
    prompts_dir="prompts",
) -> str:
    """Answer a free-text question. Requires an LLM backend (raises LLMError if none)."""
    outlook = summarise_outlook(location, readings, config, now)
    guidance = _collect_guidance(playbooks)
    emergency = ", ".join(f"{service} {number}" for service, number in config.emergency.items())
    prompt = load_prompt(Path(prompts_dir), ADVISOR_PROMPT_FILE.removesuffix(".md"))
    system = prompt.format(
        country=config.country,
        language=config.language,
        outlook=outlook,
        guidance=guidance,
        emergency=emergency,
    )
    return llm.generate(system, question, max_tokens=500)


def _collect_guidance(playbooks: List[Playbook]) -> str:
    seen = set()
    actions: List[str] = []
    warnings: List[str] = []
    for playbook in playbooks:
        for action in playbook.protective_actions:
            if action.lower() not in seen:
                seen.add(action.lower())
                actions.append(action)
        for warning in playbook.warning_signs:
            key = "w:" + warning.lower()
            if key not in seen:
                seen.add(key)
                warnings.append(warning)
    text = "Protective actions:\n" + "\n".join("- " + a for a in actions)
    if warnings:
        text += "\n\nEmergency warning signs (advise calling for help):\n" + "\n".join(
            "- " + w for w in warnings
        )
    return text
