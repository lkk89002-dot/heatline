"""Opt-in subscriber roster loading.

The roster is the ONLY place Heatline holds contact details, and it lives in a
file you provide (never committed — see .gitignore) to keep deployments in
control of their own data (privacy by design, national data ownership). Each
line is a JSON object:

    {"audience": "outdoor_worker", "channel": "whatsapp", "recipient": "+1876..."}

`recipient` is opaque to Heatline (a phone number, a Messenger id, anything the
channel understands). With no roster file, runs are console/bulletin only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Subscriber:
    audience: str
    channel: str
    recipient: str


class RosterError(ValueError):
    """Raised when a roster file exists but is malformed."""


def load_roster(path) -> List[Subscriber]:
    path = Path(path)
    if not path.exists():
        return []
    subscribers = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
            sub = Subscriber(
                audience=str(obj["audience"]).strip(),
                channel=str(obj["channel"]).strip(),
                recipient=str(obj["recipient"]).strip(),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise RosterError(f"{path}:{lineno}: invalid roster entry: {exc}")
        if not (sub.audience and sub.channel and sub.recipient):
            raise RosterError(f"{path}:{lineno}: audience, channel and recipient must all be set")
        subscribers.append(sub)
    return subscribers
