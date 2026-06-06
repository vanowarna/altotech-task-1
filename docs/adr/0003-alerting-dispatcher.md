# ADR-0003 — Alerting: Pluggable Dispatcher (webhook + structured log)

**Status:** Accepted · **Date:** 2026-06-06

## Context
When the AFDD engine detects a fault it must log the event and dispatch an alert (the assessment allows webhook, log, or queue — mock is acceptable). We want zero external dependencies for the demo, but a clean extension path to real enterprise channels.

## Decision
Implement an **`AlertDispatcher` with an adapter interface** and ship two zero-setup adapters:
- **LogAdapter** — structured JSON log line (always on; satisfies the observability requirement).
- **WebhookAdapter** — HTTP POST to a configurable URL (mockable; e.g. a local receiver).

Channels are selected by config (`ALERT_CHANNELS=log,webhook`). Adding a new channel = implementing one `send(fault)` method — no engine changes.

## Alternatives considered
- **Telegram bot.** Visually nice but needs a bot token + chat ID at demo time; dropped as a hard dependency. It remains a ~30-line adapter that can be enabled later, documented as such.
- **Message queue (Kafka/RabbitMQ).** Right answer at enterprise scale (decouples detection from delivery, enables fan-out). Overkill for the POC; named as the scale path.

## Consequences
- **+** Demo runs with no external accounts; extensibility is demonstrable (the adapter seam).
- **+** Structured logs double as the audit trail and feed Prometheus/metrics later.
- **−** No delivery guarantees in the POC (fire-and-forget). Acceptable; the queue path addresses it.

## Scale path
Swap/extend adapters to email/SMS/PagerDuty/MS Teams; route through a message queue for durability, retries, and fan-out; add per-property routing and severity-based escalation.
