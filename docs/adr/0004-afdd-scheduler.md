# ADR-0004 — AFDD Rule Scheduler: In-process APScheduler (POC)

**Status:** Accepted · **Date:** 2026-06-06

## Context
The AFDD engine must evaluate rules periodically (every 1–5 minutes) across all sites. We need scheduling for the POC without standing up broker infrastructure, while keeping a credible path to distributed execution at 100+ sites.

## Decision
Use **APScheduler** (in-process, interval triggers) inside a dedicated `afdd-engine` service container. Each rule (or rule batch) is evaluated on its configured interval. The engine is **stateless** between runs — all state (rules, faults, active-fault dedup) lives in Neo4j, so the scheduler can be replaced without touching evaluation logic.

## Alternatives considered
- **Celery + Redis/RabbitMQ.** The enterprise answer (distributed workers, retries, horizontal scale). Too heavy for a single-laptop POC; named as the scale path.
- **OS cron / Docker cron.** Simple but no in-process control, harder to test, no dynamic rule reload.
- **Temporal / cloud scheduler.** Powerful workflow orchestration; out of scope for a local POC.

## Consequences
- **+** Zero extra infra; trivial to run in compose; easy to unit-test (call the evaluator directly).
- **+** Stateless engine → the scheduler is a swappable seam.
- **−** Single-process throughput ceiling; no cross-host distribution. Bounded by design (POC = 3 sites).

## Scale path
Replace APScheduler with Celery beat + workers (or Temporal); shard evaluation jobs by `property_id`; the `Condition Evaluator` / `Fault Manager` are unchanged because they read/write only Neo4j + TimescaleDB.
