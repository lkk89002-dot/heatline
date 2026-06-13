# Privacy

Heatline is built privacy-first, in line with the Digital Public Goods Standard.

## Principles

- **Opt-in only.** Heatline contacts people who have subscribed. It never cold-
  messages numbers.
- **Minimal data.** To send an alert Heatline needs only a recipient identifier
  (a phone number or messaging id) and the audience type the person chose
  (e.g. `outdoor_worker`). It does not require names, addresses, or health
  records.
- **No PII in the codebase or open data.** Contact details live only in an
  operator-supplied roster file that is **git-ignored** (`roster.jsonl`). The
  public bulletins and JSONL exports are reproducible from open inputs and
  contain no personal data.
- **National / deployer data ownership.** The deploying health authority holds
  its own subscriber list and runs its own instance. Heatline the project never
  collects or sees user data.
- **Secrets via environment only.** API tokens are read from environment
  variables, never stored in code or config (see `.gitignore`).

## The roster

The only place contact details exist is a file you provide. Each line:

```json
{"audience": "outdoor_worker", "channel": "whatsapp", "recipient": "+18765550100"}
```

See [`roster.example.jsonl`](../roster.example.jsonl). The `recipient` value is
opaque to Heatline — it is handed to the channel adapter unchanged.

## Two-way questions

When a resident asks a question, the text is sent to the configured AI backend
to produce a grounded answer. Deployers should:

- choose a backend whose data-handling terms meet local law,
- not log message content with personal identifiers,
- disclose AI use to subscribers at opt-in.

## Onward relay (megaphone) and data minimisation

Community relayers receive **briefings**, not subscriber lists. The downstream
people a health aide or church leader reaches through their own networks are
never stored by Heatline — minimising the personal data the system holds while
still reaching people who are not direct subscribers.
