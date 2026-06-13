# Deployment

Heatline is infrastructure-light: open data in, messages out, no sensors and no
database required for a basic deployment.

## 1. Configure

Copy [`config/jamaica.yaml`](../config/jamaica.yaml) and edit for your country:

- `country`, `timezone`, `language`
- `emergency` numbers (the service whose name contains "ambulance" is used as
  the medical emergency number in messages)
- `alert_levels` — heat-index °C thresholds + minimum consecutive hours.
  **Have these reviewed and signed off by your health authority.**
- `locations` — name + latitude/longitude for each place to monitor
- `channels` — any of `console`, `jsonl`, `whatsapp`, `sms`, `messenger`

Validate before running:

```bash
heatline --config config/yourcountry.yaml check
```

## 2. Channels & credentials

Credentials come from the environment. Until set, network channels run in
**dry-run** mode (they log what would be sent), so the pipeline is fully
demonstrable with no accounts.

| Channel | Environment variables |
|---|---|
| `whatsapp` | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` (Meta WhatsApp Cloud API) |
| `messenger` | `MESSENGER_PAGE_TOKEN` (Meta Graph API) |
| `sms` | `SMS_GATEWAY_URL`, `SMS_FROM`, optional `SMS_AUTH_HEADER` (any HTTP gateway, e.g. Twilio/Vonage/national aggregator) |
| `console`, `jsonl` | none |

## 3. Subscribers (opt-in)

Create `roster.jsonl` (git-ignored — never commit real contacts) from
[`roster.example.jsonl`](../roster.example.jsonl):

```json
{"audience": "outdoor_worker", "channel": "whatsapp", "recipient": "+18765550100"}
{"audience": "community_health_aide", "channel": "whatsapp", "recipient": "+18765550111"}
```

The `community_health_aide` audience is the megaphone: those relayers get
briefings formatted for onward relay to the households they serve.

## 4. Run on a schedule

One pass = one `heatline run`. Schedule it (e.g. twice daily) with cron:

```cron
# 06:00 and 15:00 Jamaica time
0 6,15 * * *  cd /opt/heatline && ./.venv/bin/heatline run --llm >> run.log 2>&1
```

State in `state.json` carries the frequency cap between runs, so scheduling
more often is safe — it will not re-alert the same window.

## 5. Replicate to another country

Because all country specifics are in the config file, replication is: new YAML +
translated playbooks (copy `playbooks/`, translate the `messages`) + local
emergency numbers + health-authority threshold sign-off. No code changes.

## Cost

- Open-Meteo: free for non-commercial use, no key.
- WhatsApp Cloud API: free tier for service conversations.
- AI backend: optional; pennies per run, or `none` to run purely on templates.
