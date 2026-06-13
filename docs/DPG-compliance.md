# Digital Public Goods Standard — self-assessment

Heatline is designed against the [Digital Public Goods Standard](https://digitalpublicgoods.net/standard/)
(9 indicators). This is a self-assessment of the prototype; formal DPG registry
recognition will be pursued separately.

| # | Indicator | Status | Evidence |
|---|---|---|---|
| 1 | **Relevance to SDGs** | ✅ | SDG 3 (health), 13 (climate action). Reduces heat-illness risk via early warning. |
| 2 | **Open licence** | ✅ | [MIT](../LICENSE) for code; bulletins/open data under CC-BY; weather data Open-Meteo CC-BY 4.0. |
| 3 | **Clear ownership** | ✅ | Copyright held by Heatline contributors; repository and licence make ownership explicit. |
| 4 | **Platform independence** | ✅ | No mandatory proprietary dependency. Channels are swappable adapters (`channels/`); AI backend is swappable and **optional** (`llm.py`); runs anywhere Python runs. |
| 5 | **Documentation** | ✅ | [README](../README.md), [architecture](architecture.md), [deployment](deployment.md), inline module docs, 60+ tests as executable specification. |
| 6 | **Non-PII data extraction / mechanism for export** | ✅ | Open bulletins + JSONL export are reproducible from open inputs; subscriber data is never embedded. |
| 7 | **Privacy & applicable laws** | ✅ | Opt-in only, minimal data, contacts kept out of the repo and under the deploying authority's control. See [privacy.md](privacy.md). |
| 8 | **Standards & best practices** | ✅ | NOAA heat-index regression; WHO/PAHO/CDC guidance; conventional Python packaging; CI. |
| 9 | **Do no harm by design** | ✅ | Conservative sustained-heat thresholds requiring health-authority sign-off, frequency cap against alert fatigue, no medical diagnosis, LLM constrained + template fallback, emergency-first messaging. See [safety.md](safety.md). |

## Open data

Every run publishes a dated bulletin (`bulletins/archive/YYYY-MM-DD.md`) and an
optional JSONL message log. Over time this becomes a public, reproducible record
of heat-stress conditions and advisories — data Jamaica does not currently
publish — intended for release under CC-BY for use by the Ministry of Health and
CARPHA. No personal data is included.

## What is not yet done

- Formal submission to the DPG registry.
- Independent clinical review of message content (currently grounded in WHO/
  PAHO/CDC public guidance; sign-off required before live use).
- A deployment partnership with a Jamaican health authority.
