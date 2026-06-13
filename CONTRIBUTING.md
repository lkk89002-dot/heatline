# Contributing to Heatline

Thanks for your interest. Heatline is an open-source digital public good and
welcomes contributions — especially from people working on heat-health in
Jamaica, the Caribbean, and other LDCs/SIDS.

## Ways to help

- **Country configs & translations.** Add a `config/<country>.yaml` and
  translated `playbooks/`. This is the highest-impact contribution.
- **Channel adapters.** Implement the `Channel` protocol for a new provider.
- **Health review.** If you are a clinician or public-health professional,
  review the playbook message content against best practice.
- **Bug fixes & tests.**

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=heatline      # tests run fully offline (no network, no API keys)
```

## Guidelines

- Keep modules small and single-purpose; only `run.py` should touch network/
  clock/filesystem.
- Add tests for new behaviour. Alert-logic tests should not depend on the
  heat-index formula (build readings with explicit values).
- **Health and safety content must stay grounded in cited public-health
  sources** (WHO/PAHO/CDC). Do not add medical claims without a source. See
  [docs/safety.md](docs/safety.md).
- Never commit secrets or real subscriber data.

## Reporting issues

Open a GitHub issue. For anything that could affect user safety, please label it
clearly so it can be prioritised.

By contributing you agree your contributions are licensed under the
[MIT License](LICENSE).
