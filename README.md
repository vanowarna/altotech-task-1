# AltoTech — Multi-Site AFDD with Brick Schema (Graph DB Edition)

> **Detect. Diagnose. Optimize.** A multi-site Automated Fault Detection & Diagnostics
> platform that models buildings as a **Brick Schema graph** (Neo4j), ingests sensor
> readings into **TimescaleDB**, and runs a **Brick-aware AFDD engine** that surfaces
> equipment faults on a live 3D operations console.

Answers: **"What equipment needs attention, and why?"**

📐 **Full architecture overview: [`ARCHITECTURE.md`](ARCHITECTURE.md)** — read this first.

---

## One-command startup

```bash
cd deploy
cp .env.example .env          # sensible defaults work out of the box
docker compose up --build
```

Brings up the whole stack and seeds **4 properties (143 devices)**, default AFDD rules, a
backfill of history with embedded faults, then evaluates rules continuously.

| URL | What |
|---|---|
| http://localhost:8080 | **3D Fault Console** — building map, KPIs, charts, activity log |
| http://localhost:8000/docs | **Swagger UI** (OpenAPI) |
| http://localhost:8000/health | Liveness · `/ready` readiness · `/metrics` Prometheus |
| http://localhost:7474 | Neo4j Browser (explore the Brick graph; user `neo4j`, pass from `.env`) |

**The 3D building map** shows every property as a tower of rooms colored by their worst active
fault (green→red). Orbit/zoom/pan freely; **hover a room** to see its live sensor readings
(temperature, humidity, CO₂, occupancy) and fault status. KPIs show device counts, healthy vs
faulted, and live ingest rate; the activity log streams recent fault events.

**Real + synthetic data.** Three hotels are driven by a synthetic simulator with injected
faults; a fourth ("Hotel D — Live Data") is fed by a **CSV replayer** streaming AltoTech's
provided `iot_sample_data` recordings, so the demo runs on genuine sensor data too.

**Demo speed.** Defaults use a fast preset (`EVAL_INTERVAL_SECONDS=15`). Set it to `60` in
`deploy/.env` for production-realistic timing.

---

## Architecture at a glance

```
Edge (simulator + CSV replayer)
   → Ingestion API (Brick resolution via the graph)
   → TimescaleDB (readings)            Neo4j (Brick graph: topology + rules + faults)
   → AFDD engine (traverse targets → window query → evaluate → open/resolve fault → alert)
   → Dashboard (3D map) / Swagger / webhook + log
```

- **Graph (Neo4j):** `Property → Location → Device` typed by `BrickClass`, plus `Rule` and `Fault`.
- **Time-series (TimescaleDB):** high-volume readings hypertable, joined to the graph by `device_id`.
  (The boundary decision: [ADR-0002](docs/adr/0002-timeseries-boundary.md).)
- **AFDD engine:** scheduler → graph-resolved evaluator → fault manager (lifecycle + dedup) → pluggable dispatcher.

Deeper docs: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/`](docs/) (ADRs, sequence diagrams,
Brick model, scalability, AI-ready), and the [requirements traceability matrix](docs/requirements-traceability.md).

---

## Repository layout

```
services/
  api/             FastAPI — ingestion, query, rules, faults, dashboard data
  afdd-engine/     scheduler + evaluator + fault manager + dispatcher + 4 rules
  edge-simulator/  configurable synthetic sensors with embedded anomalies
  csv-replayer/    streams real sample CSVs into the hotel_live property
  dashboard/       single-page 3D console (nginx + reverse proxy to api)
packages/shared/   Brick mapping, topology builder, models, DB clients (one source of truth)
graph/             Cypher schema + idempotent topology loader
deploy/            docker-compose, .env, timescale init, topology.yaml, k8s + prometheus
docs/              ADRs, architecture, Brick design, scalability, AI-ready, RTM, wiki, DEMO
skills/            bonus Claude Code SKILL.md (Brick + AFDD)
tests/integration/ live end-to-end smoke test
ARCHITECTURE.md    reviewer-facing architecture overview
```

---

## Development & tests

```bash
pip install -r requirements-dev.txt    # shared lib + fastapi + apscheduler + httpx + pytest
./scripts/run_tests.sh                  # runs each service suite in its own process
```

27 unit tests cover the topology builder, Brick mapping, simulator anomalies, ingestion
resolution, the four rule evaluators, and the fault-manager Cypher guard.

> Each service has its own top-level `app` package, so the suites run in **separate processes**
> (a single pytest run across services would collide in `sys.modules`). CI and
> `scripts/run_tests.sh` handle this; see `.github/workflows/ci.yml`.

End-to-end against a running stack:
```bash
python tests/integration/smoke_test.py
```

---

## The four AFDD rules

| Rule | Detects | Brick class |
|---|---|---|
| Temperature Excursion | value > threshold, sustained | `Zone_Air_Temperature_Sensor` |
| Sensor Flatline | stuck sensor (≈ zero variance) | `CO2_Sensor` |
| Schedule Violation | active outside operating hours | `Occupancy_Sensor` |
| Energy Anomaly | usage > rolling baseline by % | `Electrical_Power_Sensor` |

Rules are **data** (graph nodes) with per-property overrides; new rule *types* plug in via an
evaluator registry — no code changes for new rule instances. Author new rules at
`POST /api/v1/rules` (schema in [`skills/SKILL.md`](skills/SKILL.md)).

---

## Configuration
Environment-driven (`deploy/.env`). The building topology is declarative
(`deploy/topology.yaml`) — change hotels, rooms, floors, sensors, or push interval there and
both the graph loader and simulator follow.
