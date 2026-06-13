# Safety / do-no-harm

Heat-health warning systems can cause harm if they over-alert, under-alert, or
give unsafe advice. Heatline treats these as design constraints, not
afterthoughts.

## Alert fatigue

Repeated or low-value alerts cause people to ignore warnings — a documented
failure mode of warning systems (WMO/WHO heatwave guidance). Heatline mitigates:

- **Sustained-heat thresholds.** An alert fires only when the heat index holds
  above a level for a minimum number of *consecutive daytime hours*. A brief
  spike does not page anyone.
- **One alert per location per day**, sent again only on **escalation** to a
  higher severity (`alerts.apply_frequency_cap`).
- Tiered severity (watch / warning / emergency) so the strongest language is
  reserved for the most dangerous conditions.

## Thresholds require health-authority sign-off

The thresholds in [`config/jamaica.yaml`](../config/jamaica.yaml) are grounded in
the US NWS heat-index categories and WHO/PAHO guidance, but they are **starting
points, not clinical thresholds**. They must be reviewed and signed off by the
national health authority before any live deployment, and validated against
local heat-illness data as it becomes available.

## Medical safety

- Heatline gives **protective guidance, not diagnosis or treatment.** Every
  bulletin and the advisor state this.
- The LLM is **constrained to reviewed facts** and instructed never to invent
  statistics, name medicines, or tell anyone to start/stop/change medication
  (see [`prompts/`](../prompts)). For anything clinical it defers to the
  person's clinic, doctor or pharmacist.
- **Emergency-first.** If a question or situation suggests heat stroke
  (confusion, fainting, hot skin, no sweating), the response leads with calling
  the local emergency number and how to cool the person.
- Message content is grounded in WHO, PAHO and CDC public guidance.

## Reliability / graceful degradation

- The LLM is **optional**. With no key, or on any provider error, Heatline uses
  the reviewed templates — it degrades to a dependable broadcast system, never
  to silence.
- A corrupt state file is treated as empty rather than blocking alerting.
- One bad recipient or channel never aborts the batch; `Channel.send` never
  raises, it returns a failure result.

## Scams & trust (Jamaica context)

Jamaica has seen heavy messaging-scam activity, and authorities have warned the
public against unknown WhatsApp senders. Heatline's response:

- **Opt-in only** — Heatline messages people who subscribed, never cold contacts.
- **Institutional co-branding** via the megaphone model: messages arrive through
  trusted community health aides, Red Cross and community leaders.
- Designed to run on a **verified Meta Business** number for a deploying authority.

## Known limitations

- Not yet clinically reviewed or deployed with a health authority.
- Forecast accuracy is bounded by the upstream provider (Open-Meteo / national
  models); Heatline surfaces uncertainty rather than implying certainty.
- The digital divide is real: the megaphone (human relay) and SMS exist
  precisely because the most vulnerable are often the least connected.
