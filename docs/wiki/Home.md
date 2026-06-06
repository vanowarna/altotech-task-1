# Multi-Site AFDD — Technical Wiki

Welcome to the technical documentation for the **AltoTech Multi-Site AFDD platform** — a
multi-site Automated Fault Detection & Diagnostics system that models buildings as a **Brick
Schema graph** (Neo4j), stores readings in **TimescaleDB**, and runs a **Brick-aware fault
engine**, surfaced on a live 3D operations console.

> These pages mirror [`docs/`](https://github.com/vanowarna/altotech-task-1/tree/main/docs)
> and [`ARCHITECTURE.md`](https://github.com/vanowarna/altotech-task-1/blob/main/ARCHITECTURE.md)
> in the repository.

## Contents
- **[System Architecture](System-Architecture)** — components, connectivity, multi-tenancy.
- **[Sequence Diagrams](Sequence-Diagrams)** — ingestion, the AFDD cycle, fault lifecycle, dashboard reads.
- **[Architecture Decisions](Architecture-Decisions)** — ADRs (graph DB, time-series boundary, alerting, scheduler, framework).
- **[Brick Schema Design](Brick-Schema-Design)** — how the Brick ontology maps to the graph and resolution at ingestion.
- **[Running the System](Running-the-System)** — one-command startup, URLs, services, demo.
- **[API Reference](API-Reference)** — the `/api/v1` surface.

## TL;DR
Buildings are graphs, and Brick Schema is a graph. Topology + semantics live in **Neo4j**;
the high-volume reading firehose lives in a **TimescaleDB** hypertable; they join on
`device_id`. The **AFDD engine** resolves rule targets by graph traversal, evaluates
time-windowed conditions, manages a fault lifecycle, and alerts. Everything starts with one
`docker compose up`.

## Key design decision
The **graph vs. time-series boundary** ([ADR-0002](Architecture-Decisions)): slow,
relationship-rich topology in the graph; the high-write reading stream in a hypertable. Each
store does what it is best at.

## What's modeled
**4 properties / 143 devices** — three hotels driven by a synthetic simulator with injected
faults, and a fourth ("Hotel D — Live Data") fed by a CSV replayer streaming AltoTech's real
sample recordings.
