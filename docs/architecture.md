# Architecture

Heatline is a small, modular pipeline. Each stage is one module with a single
responsibility; only [`run.py`](../heatline/run.py) touches the network, the
clock and the filesystem, so the rest is pure and easy to test offline.

```
                       config/jamaica.yaml   playbooks/*.yaml   prompts/*.md
                              │                    │                 │
                              ▼                    ▼                 ▼
  Open-Meteo ──▶ forecast ──▶ heat_index ──▶ alerts ──▶ compose ──▶ channels ──▶ WhatsApp/SMS/
   (free API)    (fetch +     (NOAA           (detect    (per-       (adapters)   Messenger
                  parse)       regression)     windows +  audience,                + console
                                               cap)       LLM opt.)   │            + jsonl export
                                                                      ▼
                                                                  bulletin (public .md + open data)
                              resident question ──▶ advisor ──▶ (LLM grounded in forecast + guidance)
```

## Modules

| Module | Responsibility |
|---|---|
| `forecast.py` | Fetch + validate Open-Meteo hourly data; compute heat index per hour |
| `heat_index.py` | NOAA/NWS Rothfusz heat-index regression (unit-tested vs chart values) |
| `config.py` | Load + validate the one-file country configuration |
| `alerts.py` | Detect sustained heat-stress windows; enforce the frequency cap |
| `compose.py` | Render audience messages from playbooks; optional LLM personalisation |
| `llm.py` | Swappable AI backend (Anthropic / OpenAI / none) behind one function |
| `advisor.py` | Two-way Q&A grounded in the forecast and reviewed guidance |
| `channels/` | Delivery adapters implementing one `Channel` protocol |
| `bulletin.py` | Public daily markdown bulletin + dated archive (open-data seed) |
| `roster.py` / `state.py` | Opt-in subscriber list; frequency-cap state |
| `run.py` | Orchestrator — wires the stages together for one pass |
| `cli.py` | `heatline check | run | ask` |

## Key design decisions

- **Config-driven, not code-driven.** A new country is a new YAML file. This is
  what makes the "adapts to any SIDS/LDC" claim real rather than aspirational.
- **The LLM is optional and constrained.** Templates are the source of truth;
  the model only rewrites them for an audience, and any failure falls back to
  the template. Heatline degrades to a reliable broadcast system, never to
  nothing. See [safety.md](safety.md).
- **Alerting logic is decoupled from the heat-index formula.** Alert tests
  build readings with explicit heat-index values, so warning behaviour is
  verified independently of the regression.
- **No PII in the core.** Contact details live only in an operator-supplied,
  git-ignored roster file. See [privacy.md](privacy.md).
- **Sustained-heat thresholds + one-alert-per-day cap.** Heat illness risk is
  about duration, and over-alerting destroys trust — both are first-class.

## Data flow for one alert

1. For each location, `forecast.fetch_hourly` pulls a 7-day hourly forecast and
   `heat_index` annotates every hour.
2. `alerts.detect_windows` finds, per day, the most severe level whose threshold
   holds for its minimum consecutive daytime hours.
3. `alerts.apply_frequency_cap` drops anything already alerted at the same or
   lower severity (state in `state.json`).
4. `compose.compose_for_window` renders one message per audience playbook,
   optionally rewriting via `llm` for the audience.
5. `run._deliver` echoes to console/jsonl and sends to opt-in subscribers on
   their chosen channel.
6. `bulletin.write_bulletin` publishes the public outlook and archives it.
