# Multi-Site AFDD — Technical Wiki

Welcome to the technical documentation for the **AltoTech Multi-Site AFDD platform**.
This wiki is the design-first record: architecture, diagrams, decisions, and the Brick
Schema model. (These pages mirror [`docs/`](../) in the repository.)

## Contents
- **[System Architecture](System-Architecture)** — components, connectivity, multi-tenancy.
- **[Sequence Diagrams](Sequence-Diagrams)** — ingestion, the AFDD evaluation cycle, fault lifecycle.
- **[Architecture Decisions](Architecture-Decisions)** — ADRs (graph DB, time-series boundary, alerting, scheduler, framework).
- **[Brick Schema Design](Brick-Schema-Design)** — how the Brick ontology maps to the graph and how resolution works at ingestion.

## TL;DR
Buildings are graphs, and Brick Schema is a graph. We model topology + semantics in
**Neo4j**, store high-volume readings in **TimescaleDB**, and run a **Brick-aware AFDD
engine** that resolves rule targets by graph traversal, evaluates time-windowed
conditions, manages a fault lifecycle, and alerts. The whole stack starts with one
`docker compose up`.

## Key design decision
The **graph vs. time-series boundary** ([ADR-0002](Architecture-Decisions)): slow,
relationship-rich topology in the graph; the high-write reading firehose in a
hypertable; joined by `device_id`. Each store does what it is best at.

## Quick links
- Repo `README` — one-command startup and URLs.
- [Requirements Traceability Matrix](../requirements-traceability.md) — every assessment requirement → where it's satisfied.
- [Scalability](../architecture/scalability.md) · [AI-Ready](../architecture/ai-ready.md) · [External Integration](../brick-schema/external-integration.md)
