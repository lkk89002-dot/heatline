# Heatline

**Open-source AI heat-health early warning and advisory — built for Jamaica, designed for replication across Caribbean SIDS and other LDCs/SIDS.**

[![CI](https://github.com/tom231826-svg/heatline/actions/workflows/ci.yml/badge.svg)](https://github.com/tom231826-svg/heatline/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

> ⚠️ **Status: working prototype.** Heatline runs end-to-end today against live
> [Open-Meteo](https://open-meteo.com) forecasts. It is **not yet deployed with a
> health authority** and its alert thresholds and message content **must be
> signed off by qualified health professionals before any live use.** It is
> advisory information, not a medical service.

---

## The problem

Extreme heat is one of Jamaica's clearest climate-health hazards. In 2024,
people in Jamaica were exposed to 48 heatwave days on average, 47 of which the
Lancet Countdown country data attributes to climate change; the Ministry of
Health and Wellness has warned that excessive heat stress can be "potentially
fatal." Jamaica has weather alerts, health advisories and regional
climate-health bulletins, but vulnerable residents still lack a last-mile,
personalized heat-health advisory and surveillance channel.

Heatline fills that gap.

## What it does

```
Open-Meteo forecast → heat-index (NOAA) → alert-window detection
   → audience-specific message (template, optionally AI-personalised)
   → WhatsApp / SMS / Messenger / bulletin   +   two-way Q&A
```

1. **Monitors** 7-day forecasts for every configured location and computes the
   NOAA heat index for every hour.
2. **Detects** dangerous heat-stress windows using configurable, sustained-heat
   thresholds (brief spikes don't page anyone; an at-most-one-alert-per-day cap
   prevents alert fatigue).
3. **Composes** plain-language protective guidance tailored to each audience —
   outdoor workers, older adults' caregivers, people with chronic illness,
   community health aides, and the general public — with optional AI
   personalisation and voice-note scripts for low-literacy and elderly users.
4. **Delivers** through Jamaica's dominant channel (WhatsApp) plus SMS and
   Messenger, and publishes a public daily bulletin.
5. **Answers** two-way questions a broadcast can't — *"My mother has
   hypertension; is tomorrow safe for the market?"* — grounded in the actual
   forecast and reviewed guidance.

### The megaphone model

Health chatbots succeed when **trusted institutions amplify them**, not as
direct-to-consumer apps. Heatline is built for that: alongside individual
opt-in subscribers, **community health aides, Red Cross volunteers and
community/church leaders** receive ward-level briefings formatted for onward
relay (the `community_health_aide` playbook + the `jsonl` export channel), and
**family caregivers** are prompted to check on elderly relatives — the
most heat-vulnerable, least-connected group.

## Quickstart

```bash
git clone https://github.com/tom231826-svg/heatline.git
cd heatline
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 1. Validate the Jamaica configuration and playbooks (no network)
heatline check

# 2. Run against LIVE Jamaica forecasts and publish a bulletin
heatline run --channels console

# 3. See the full alert path on an illustrative heat-wave scenario
heatline run --fixture examples/illustrative_heat_event.json \
             --channels console,jsonl --now 2026-06-13T06:00

# 4. Ask a question (needs an AI key — see "AI backends")
export ANTHROPIC_API_KEY=sk-...
heatline ask --location Kingston "I work construction. Is tomorrow safe?"
```

`heatline run` with no dangerous heat in the forecast produces a calm "no
alert" bulletin — which is the correct, honest output most days. Use the
illustrative fixture to exercise the alert path on demand.

## AI backends (swappable, optional)

Heatline **never requires** an LLM. With no key configured it uses static
playbook templates grounded in public guidance, so delivery is never blocked by a
missing key or a provider outage. To enable AI personalisation, set one of:

| Variable | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | use Claude (default model `claude-sonnet-4-6`) |
| `OPENAI_API_KEY` | use OpenAI (default model `gpt-4o-mini`) |
| `HEATLINE_LLM_PROVIDER` | force `anthropic`, `openai`, or `none` |
| `HEATLINE_LLM_MODEL` | override the model id |

Then add `--llm` to `heatline run`. The model is constrained to the reviewed
facts and is instructed never to invent medical content; any failure falls back
to the template (see [docs/safety.md](docs/safety.md)).

## Adapting to another country

Everything country-specific lives in **one file**. Copy
[`config/jamaica.yaml`](config/jamaica.yaml), change the locations, thresholds,
language, channels and emergency numbers, and run. No code changes. See
[docs/deployment.md](docs/deployment.md).

## Documentation

- [Architecture](docs/architecture.md) — how the pieces fit together
- [Digital Public Goods alignment](docs/DPG-compliance.md) — against the DPG Standard
- [Privacy](docs/privacy.md) — opt-in, minimal data, national data ownership
- [Safety / do-no-harm](docs/safety.md) — thresholds, alert fatigue, medical safeguards
- [Deployment](docs/deployment.md) — channels, scheduling, replication

## Development

```bash
pip install -e ".[dev]"
pytest --cov=heatline        # 60+ tests, ~90% coverage, no network required
```

## License & data

Code under the [MIT License](LICENSE). Weather data by
[Open-Meteo.com](https://open-meteo.com) (CC-BY 4.0). Heat-health guidance
grounded in [WHO](https://www.who.int/news-room/fact-sheets/detail/climate-change-heat-and-health),
[PAHO](https://www.paho.org/en/documents/heatwaves-guide-health-based-actions) and
[CDC](https://www.cdc.gov/extreme-heat/about/) public materials.
Problem framing also draws on the
[Lancet Countdown Jamaica 2025 data sheet](https://lancetcountdown.org/wp-content/uploads/2025/11/Jamaica_Lancet-Countdown_2025_Data-Sheet.pdf)
and a
[Jamaica Ministry of Health and Wellness heat advisory](https://www.moh.gov.jm/jamaicans-urged-to-reduce-heat-exposure/).

## Acknowledgements

Built as an entry to the **UNFCCC AI for Climate Action Award (AICA) 2026**.
Heat-health early-warning evidence base includes the Ahmedabad Heat Action Plan
(Hess et al., 2018) and PAHO/WHO Caribbean heat-health guidance.
