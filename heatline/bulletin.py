"""Render the public daily heat-health bulletin (markdown).

The bulletin doubles as Heatline's open dataset seed: every run archives the
detected alert windows, so the repository accumulates a public, dated record
of heat-stress conditions and advisory decisions for later review.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .alerts import AlertWindow
from .compose import OutboundMessage, hour_label, human_date
from .config import CountryConfig

REPO_URL = "https://github.com/tom231826-svg/heatline"

BADGES = {"watch": "🟡 WATCH", "warning": "🟠 WARNING", "emergency": "🔴 EMERGENCY"}


def write_bulletin(
    directory,
    config: CountryConfig,
    windows: List[AlertWindow],
    messages: List[OutboundMessage],
    now: datetime,
) -> Path:
    directory = Path(directory)
    (directory / "archive").mkdir(parents=True, exist_ok=True)
    text = render_bulletin(config, windows, messages, now)
    latest = directory / "latest.md"
    latest.write_text(text, encoding="utf-8")
    (directory / "archive" / f"{now.date().isoformat()}.md").write_text(text, encoding="utf-8")
    return latest


def render_bulletin(
    config: CountryConfig,
    windows: List[AlertWindow],
    messages: List[OutboundMessage],
    now: datetime,
) -> str:
    rank = {level.name: i for i, level in enumerate(config.levels)}
    thresholds = {level.name: level.hi_c for level in config.levels}
    by_location: Dict[str, List[AlertWindow]] = defaultdict(list)
    for window in windows:
        by_location[window.location].append(window)

    lines = [
        f"# {config.country} Heat-Health Bulletin — {now.strftime('%A')} {now.day} {now.strftime('%B %Y')}",
        "",
        f"_Generated {now.strftime('%Y-%m-%d %H:%M %Z')} by [Heatline]({REPO_URL}) from"
        " [Open-Meteo](https://open-meteo.com) forecasts (CC-BY 4.0)."
        " Advisory information only — not a medical service._",
        "",
    ]

    if not windows:
        lines += ["**🟢 No heat-stress alert windows detected in the next 7 days.**", ""]
    else:
        lines += [
            "## 7-day outlook",
            "",
            "| Location | Highest level | Date | Peak heat index | Consecutive hours |",
            "|---|---|---|---|---|",
        ]
        for location in config.locations:
            location_windows = by_location.get(location.name, [])
            if not location_windows:
                lines.append(f"| {location.name} | 🟢 none | — | — | — |")
                continue
            worst = min(location_windows, key=lambda w: rank.get(w.level, 99))
            badge = BADGES.get(worst.level, worst.level.upper())
            lines.append(
                f"| {location.name} | {badge} | {human_date(worst.date)} |"
                f" {worst.peak_hi_c:.0f} °C | {worst.hours} |"
            )
        lines += ["", "## Alert windows", ""]
        for window in sorted(windows, key=lambda w: (w.date, rank.get(w.level, 99))):
            badge = BADGES.get(window.level, window.level.upper())
            threshold = thresholds.get(window.level)
            threshold_label = f" ≥ {threshold:.0f} °C" if threshold is not None else ""
            lines.append(
                f"- **{human_date(window.date)} — {window.location}**: {badge}, heat index"
                f"{threshold_label} for {window.hours} consecutive hour(s),"
                f" peaking near {window.peak_hi_c:.0f} °C around {hour_label(window.peak_time)}."
            )
        lines.append("")

    lines += ["## Today's advisory messages", ""]
    if messages:
        lines.append(
            "_One message per audience for each newly issued alert"
            f" (generator: {messages[0].generator})._"
        )
        lines.append("")
        for message in messages:
            quoted = message.text.replace("\n", "\n> ")
            lines += [f"**{message.audience}** — {message.location} ({BADGES.get(message.level, message.level)})", "", f"> {quoted}", ""]
    else:
        lines += [
            "_No new advisories this run: no alert window starts within the next 48 hours,"
            " or today's alerts were already issued (frequency cap — see archive)._",
            "",
        ]

    emergency = ", ".join(f"{service} {number}" for service, number in config.emergency.items())
    lines += [
        "---",
        "",
        f"**Emergency numbers ({config.country}):** {emergency}",
        "",
        "**Grounding sources:** [WHO — Heat and health](https://www.who.int/news-room/fact-sheets/detail/climate-change-heat-and-health) ·"
        " [PAHO — Heatwaves: a guide for health-based actions](https://www.paho.org/en/documents/heatwaves-guide-health-based-actions) ·"
        " [CDC — Extreme heat](https://www.cdc.gov/extreme-heat/about/) ·"
        " [NWS — The heat index](https://www.weather.gov/safety/heat-index)",
        "",
    ]
    return "\n".join(lines)
