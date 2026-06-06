# AltoTech — Multi-Site AFDD with Brick Schema (Graph DB Edition)

> **Detect. Diagnose. Optimize.** A multi-site Automated Fault Detection & Diagnostics
> platform that models 3 hotels as a **Brick Schema graph** (Neo4j), ingests sensor
> readings into **TimescaleDB**, and runs a **Brick-aware AFDD engine** that detects
> equipment faults and surfaces them on a clean, real-time dashboard.

Answers the question: **"What equipment needs attention, and why?"**

---

## One-command startup

```bash
cd deploy
cp .env.example .env          # optional; sensible defaults work out of the box
docker compose up --build
```

That brings up the whole stack and **seeds 3 hotels (125 devices), default AFDD rules,
2 hours of backfilled history with embedded faults**, then evaluates rules every 60s.

| URL | What |
|---|---|
| http://localhost:8080 | **Fault Console** dashboard (light/dark, mobile) |
| http://localhost:8000/docs | **Swagger UI** (OpenAPI) for the API |
| http://localhost:8000/health | Liveness · `/ready` for readiness · `/metrics` for Prometheus |
| http://localhost:7474 | Neo4j Browser (explore the Brick graph; user `neo4j` / pass from `.env`) |

Within a minute the dashboard shows active faults (a temperature excursion, a CO₂
sensor flatline, and — after a few minutes of live data — an energy anomaly).

---

## Architecture at a glance

```
Edge Simulator → Ingestion API (Brick resolution via graph) → TimescaleDB
                                   │                                 ▲
                                   ▼                                 │ window queries
                              Neo4j (Brick graph) ◀── AFDD Engine ───┘
                                   │  faults                │ alerts
                                   ▼                        ▼
                         Dashboard / Swagger          webhook + log
```

- **Graph (Neo4j):** topology + Brick semantics — `Property → Location → Device`,
  typed by `BrickClass`, plus `Rule` and `Fault` nodes.
- **Time-series (TimescaleDB):** the high-volume readings hypertable, joined to the
  graph by `device_id`. (See [ADR-0002](docs/adr/0002-timeseries-boundary.md) — the
  key design decision.)
- **AFDD engine:** scheduler → graph-resolved condition evaluator → fault manager
  (lifecycle + dedup) → pluggable dispatcher.

Full design docs: [`docs/`](docs/) — architecture, sequence diagrams, ADRs, Brick
model, scalability, AI-ready notes, and a [requirements traceability matrix](docs/requirements-traceability.md).

---

## Repository layout

```
services/
  api/             FastAPI — ingestion, query, rules, faults, dashboard data
  afdd-engine/     scheduler + evaluator + fault manager + dispatcher + 4 rules
  edge-simulator/  configurable sensor simulator with embedded anomalies
  dashboard/       single-page Fault Console (nginx)
packages/shared/   Brick mapping, topology builder, models, DB clients (one source of truth)
graph/             Cypher schema + idempotent topology loader
deploy/            docker-compose, env, timescale init, k8s + prometheus (bonus)
docs/              ADRs, architecture, Brick design, scalability, RTM (wiki source)
skills/            bonus Claude Code SKILL.md (Brick + AFDD)
```

---

## Development & tests

```bash
# unit tests (no DB needed — pure logic)
pip install -e packages/shared pytest
python -m pytest packages/shared/tests
(cd services/edge-simulator && python -m pytest tests)
(cd services/api && python -m pytest tests)
(cd services/afdd-engine && python -m pytest tests)
```

24 unit tests cover the topology builder, Brick mapping, simulator anomalies, ingestion
resolution, and all four rule evaluators.

---

## The four AFDD rules

| Rule | Detects | Brick class |
|---|---|---|
| Temperature Excursion | value > threshold, sustained | `Zone_Air_Temperature_Sensor` |
| Sensor Flatline | stuck sensor (≈ zero variance) | `CO2_Sensor` |
| Schedule Violation | active outside operating hours | `Occupancy_Sensor` |
| Energy Anomaly | usage > rolling baseline by % | `Electrical_Power_Sensor` |

Rules are **data** (graph nodes) with per-property overrides; new rule *types* plug in
via an evaluator registry — no code changes for new rule instances. Author new rules at
`POST /api/v1/rules` (schema in [`skills/SKILL.md`](skills/SKILL.md)).

---

## Configuration
All config is environment-driven (`deploy/.env`). The building topology is declarative
(`deploy/topology.yaml`) — change hotels, rooms, floors, sensors, or push interval there
and both the graph loader and simulator follow.
