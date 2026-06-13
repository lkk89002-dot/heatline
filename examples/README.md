# Examples

| File | What it is |
|---|---|
| `illustrative_heat_event.json` | **Illustrative, not real.** A real Open-Meteo response with daytime temperatures on days 1–2 raised into the 36–38 °C range observed during Jamaica's 2024–2025 heat waves, so the alert path can be demonstrated on demand. Real captured data lives in [`../tests/fixtures/jamaica_live.json`](../tests/fixtures/jamaica_live.json). |
| `sample_bulletin_alert.md` | Bulletin generated from the illustrative event — shows the full warning + advisory output. |
| `sample_bulletin_calm.md` | Bulletin generated from **real** current Jamaica forecast data — the honest "no dangerous heat" output most days produce. |

## Reproduce

```bash
# Alert scenario
heatline run --fixture examples/illustrative_heat_event.json \
             --channels console,jsonl --now 2026-06-13T06:00

# Real forecast (whatever the weather is today)
heatline run --channels console
```

The alert bulletin's heat-index values (50–54 °C) are deliberately extreme to
exercise the emergency tier; real Jamaican conditions in June 2026 peaked around
36–37 °C heat index — just below the watch threshold, which is the intended
calibration.
