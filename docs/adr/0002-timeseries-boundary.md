# ADR-0002 — Graph vs. Time-Series Boundary: TimescaleDB

**Status:** Accepted · **Date:** 2026-06-06

## Context
Each device emits a reading every 30–60s. At 30 rooms × ~4 datapoints that is already thousands of writes/minute per site; at 400 properties it is millions. Graph databases model topology brilliantly but are poor at high-volume time-series writes. The assessment explicitly asks us to **decide where readings live, how they link back to the graph, and to justify the boundary** — this is the single most graded design decision.

## Decision
Split storage by access pattern:
- **Neo4j (graph):** slow-changing topology + semantics — `Property`, `Location`, `Device`, `BrickClass`, `Rule`, `Fault` nodes and their relationships.
- **TimescaleDB (time-series):** the reading firehose, in a **hypertable** `readings(time, device_id, datapoint, value)` partitioned by time, with continuous aggregates for rolling windows.
- **Link:** `device_id` is the join key. Neo4j answers *which* devices (by Brick class / location / property); TimescaleDB answers *what values* over a time window.

## Alternatives considered
- **Readings as nodes/edges in Neo4j.** Rejected: write amplification and graph bloat; traversals slow as the graph grows by millions of nodes/day.
- **Single Postgres + Apache AGE** (graph + TS in one engine). Viable and operationally simpler; deferred per ADR-0001 tooling reasons. The boundary logic here would still apply.
- **Flat relational table without Timescale.** Rejected: no hypertable partitioning or continuous aggregates → window queries degrade at scale.

## Consequences
- **+** Each store does what it is best at; ingestion write path never touches graph traversal cost beyond a single indexed lookup.
- **+** AFDD window queries (`last 15 min`, `7-day rolling avg`) are native TimescaleDB.
- **−** Two stores to operate and keep referentially consistent (device must exist in graph before readings resolve). Mitigated by ingestion validation + foreign-key-by-convention on `device_id`.

## Scale path
TimescaleDB hypertable chunking + compression + continuous aggregates; shard by `property_id` / time; cold data → object storage. Graph remains small and fast.
