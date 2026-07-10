# Code Walkthrough — what each file does and how they connect

> Personal reference (git-ignored). Read top to bottom to understand the whole system
> file-by-file. Follow the data: a sensor reading enters at the simulator/replayer, is
> resolved and stored by the API, evaluated by the engine, and shown on the dashboard.

---

## The mental model (5 sentences)

1. The **simulator** and **CSV replayer** are fake/real sensors that POST readings to the API.
2. The **API** looks up each device in the **Neo4j graph** to find its Brick class + room + hotel, then writes the reading to **TimescaleDB**.
3. The **AFDD engine** wakes on a timer, asks the graph "which devices are this rule's Brick type?", pulls their recent readings from TimescaleDB, and checks the rule.
4. When a rule trips, the engine writes a **Fault** node in Neo4j and fires an alert.
5. The **dashboard** reads the API and draws the 3D building map + charts + activity log.

Everything shares one library, `packages/shared/afdd_shared`, so all services agree on the
Brick mapping, the building layout, the data models, and how to talk to the databases.

---

## 1. Shared library — `packages/shared/afdd_shared/`  (the spine)

| File | What it does | Used by |
|---|---|---|
| `brick.py` | The **Brick mapping**: `temperature → brick:Zone_Air_Temperature_Sensor`, etc. One source of truth for sensor type → Brick class + unit. | simulator, loader, API ingest |
| `topology.py` | The **topology builder**: turns `topology.yaml` (declarative hotels) into concrete `Property/Location/Device` objects with deterministic IDs (`hotel_a-r101-temperature`). | loader (creates graph), simulator + replayer (know device IDs) |
| `models.py` | **Pydantic models** for requests/responses: `Reading`, `ResolvedReading`, `RuleIn/Out`, `FaultOut`, etc. Note `Reading` has **no** `brick_class` (resolved later). | API, tests |
| `config.py` | Reads env vars (`NEO4J_*`, `TS_*`) into a `Settings` object; builds the Postgres DSN. | every service |
| `logging_setup.py` | Structured **JSON logging** (one line per event). | every service |
| `neo4j_client.py` | Async Neo4j wrapper. Key methods: `resolve_devices_bulk()` (ingestion), `devices_by_brick_class()` (engine + queries). Also silences harmless Neo4j notifications. | API, engine, loader |
| `timescale.py` | Async TimescaleDB wrapper. Methods: `insert_readings`, `latest`, `range`, `window` (engine), `baseline_avg` (energy rule), `count_since` (ingest rate), `latest_all` (3D hover). | API, engine |
| `rules.py` | The rule **vocabulary**: `CONDITION_TYPES` (the 4 rule types + their params) and `DEFAULT_RULES` seeded on startup. | engine seed, API validation |

**How it connects:** the loader uses `topology.py` + `brick.py` to build the graph; the
simulator uses the same `topology.py` so its device IDs match exactly; the API uses
`neo4j_client` + `timescale` + `models`; the engine uses `neo4j_client` + `timescale` + `rules`.

---

## 2. Graph — `graph/`

| File | What it does |
|---|---|
| `schema.cypher` | Uniqueness **constraints** + indexes (e.g. unique `Device.id`) so device resolution is O(1). |
| `load_topology.py` | The **one-shot loader**: applies the schema, creates a `BrickClass` node per Brick class, then `MERGE`s every `Property/Location/Device` and their relationships from `topology.yaml`. Idempotent — safe to re-run. Runs as the `graph-loader` container. |

---

## 3. Time-series init — `deploy/timescale/init.sql`

Creates the `readings` **hypertable** (partitioned by time), indexes matching the query
patterns, and a `readings_hourly` **continuous aggregate** (cheap rolling stats for the energy
rule). Runs automatically on first TimescaleDB container start.

---

## 4. Edge simulator — `services/edge-simulator/`

| File | What it does |
|---|---|
| `generators.py` | **Pure** functions (no I/O, unit-tested): realistic diurnal values per datapoint + the 4 anomaly kinds (temperature_spike, flatline, schedule_violation, energy_anomaly). |
| `simulator.py` | Loads topology, **excludes `hotel_live`**, binds anomalies to devices, backfills ~30 min of history, then streams live batches to `POST /ingest/batch`. |
| `config.yaml` | Push interval, seed, backfill window, excluded properties, and the list of injected anomalies. |

**Connects to:** the API (HTTP). Anomalies here are what later become faults in the engine.

---

## 5. CSV replayer — `services/csv-replayer/`

| File | What it does |
|---|---|
| `replayer.py` | Reads the **real** sample CSVs (`iot_sample_data`), maps columns → `hotel_live` device IDs, **remaps timestamps to recent** wall-clock, backfills then streams to `POST /ingest/batch`. Exits gracefully if the CSVs are absent. |

**Connects to:** the API (HTTP) and the `hotel_live` devices created by the loader. This is a
worked example of how a *real* sensor feed would integrate.

---

## 6. API — `services/api/app/`

| File | What it does |
|---|---|
| `main.py` | Builds the FastAPI app, CORS, lifespan (opens/closes DB clients), mounts routers, exposes `/metrics`, `/docs`. |
| `deps.py` | Holds the long-lived Neo4j + TimescaleDB clients; `startup()/shutdown()` lifecycle; `get_neo4j()/get_timescale()` accessors. |
| `routers/ingest.py` | **The integration point.** Bulk-resolves device IDs against the graph, converts to `ResolvedReading` (numeric vs occupancy text), writes to TimescaleDB. Rejects unknown devices. |
| `routers/query.py` | `GET /devices/{id}/latest` and `/readings?from&to` from TimescaleDB. |
| `routers/devices.py` | Minimal Property/Device CRUD as graph nodes + `GET /devices?brick_class=` traversal. |
| `routers/rules.py` | Rule CRUD + enable/disable (per property via `property_overrides`). Params stored as JSON strings on the `Rule` node. |
| `routers/faults.py` | List/filter faults, fault details with context, ack/resolve/notes (lifecycle transitions). |
| `routers/dashboard.py` | `/summary` (fault counts), `/stats` (device counts + ingest rate), `/topology` (building + per-room fault status + device list, for 3D), `/readings` (latest value per device, for hover). |
| `routers/health.py` | `/health` (liveness), `/ready` (checks both DBs). |

**Connects to:** Neo4j (resolution, CRUD, faults) + TimescaleDB (readings). Consumed by the
simulator/replayer (ingest) and the dashboard (read).

---

## 7. AFDD engine — `services/afdd-engine/app/`

| File | What it does |
|---|---|
| `main.py` | Waits for DBs, **seeds default rules**, starts APScheduler (`EVAL_INTERVAL_SECONDS`), runs one cycle immediately (guarded), keeps the process alive. |
| `evaluator.py` | The **orchestrator**: loads enabled rules, for each rule resolves target devices by Brick class, pulls each device's window (+ baseline for energy), runs the evaluator, opens/resolves faults, dispatches alerts. Each device is isolated in `try/except`. |
| `fault_manager.py` | Creates faults (with `WHERE NOT EXISTS` **dedup**) and resolves them; links `Fault -[:detectedOn]-> Device` and `-[:raisedBy]-> Rule`. |
| `dispatcher.py` | Pluggable `AlertDispatcher` with `LogAdapter` + `WebhookAdapter`, selected by `ALERT_CHANNELS`. |
| `seed.py` | Idempotently writes `DEFAULT_RULES` (from `afdd_shared/rules.py`) as `Rule` nodes. |
| `rules/base.py` | The evaluator **registry** (`@register`), `EvalInput/EvalResult`, and helpers (`within_last_minutes`, `numeric_values`). |
| `rules/threshold.py` | Temperature excursion: value breaches threshold for a sustained duration. |
| `rules/flatline.py` | Stuck sensor: near-zero variance over the window. |
| `rules/schedule.py` | Active outside operating hours (time-of-day aware). |
| `rules/energy.py` | Recent average exceeds the rolling baseline by a %. |

**Connects to:** Neo4j (rules, targets, faults) + TimescaleDB (windows, baseline). Writes the
`Fault` nodes the dashboard shows.

---

## 8. Dashboard — `services/dashboard/`

| File | What it does |
|---|---|
| `index.html` | The whole single-page console: KPI strip, severity doughnut + bars, scrollable activity log, and the **Three.js 3D building map** (OrbitControls, fit-all camera, glassy rooms colored by fault, property labels, room hover showing live readings). Fetches `/dashboard/{stats,summary,topology,readings}` + `/faults` every 10s. |
| `nginx.conf` | Serves the SPA and **reverse-proxies `/api`** to the API container (same-origin → no CORS issues in the browser). |
| `Dockerfile` | nginx image with the SPA + config. |

**Connects to:** the API (through the nginx proxy).

---

## 9. Deployment — `deploy/`

| File | What it does |
|---|---|
| `docker-compose.yml` | Orchestrates all 8 services with healthchecks + ordered `depends_on` (DBs healthy → loader runs → api/engine/sim/replayer start). |
| `topology.yaml` | The declarative buildings (3 synthetic + `hotel_live`). Change hotels/rooms/sensors here. |
| `.env.example` | Dev/prod env values (fast demo preset by default). |
| `timescale/init.sql` | Hypertable + continuous aggregate (see §3). |
| `loader/Dockerfile` | Builds the one-shot graph loader image. |
| `prometheus/prometheus.yml` | Scrape config for `/metrics` (bonus). |
| `k8s/manifests.yaml` | Kubernetes equivalent of the compose topology (bonus). |

---

## 10. Tests + CI

| File | What it does |
|---|---|
| `packages/shared/tests/test_topology.py` | Topology builder + Brick mapping (5 tests). |
| `services/edge-simulator/tests/test_generators.py` | Value + anomaly generators (6 tests). |
| `services/api/tests/test_ingest_logic.py` | Ingestion + resolution with fakes (4 tests). |
| `services/afdd-engine/tests/test_rules.py` | The 4 rule evaluators (9 tests). |
| `services/afdd-engine/tests/test_fault_manager.py` | Regression guard: every `$param` in the fault Cypher is supplied (3 tests). |
| `tests/integration/smoke_test.py` | Live end-to-end against a running stack. |
| `.github/workflows/ci.yml` | Lint + **per-service** unit tests (separate processes — each service has its own `app` package) + image builds. |
| `scripts/run_tests.sh` | Runs all suites locally, one process each. |

---

## 11. Follow the data (end-to-end trace)

1. `simulator.py` builds a batch → `POST /ingest/batch`.
2. `routers/ingest.py` → `neo4j_client.resolve_devices_bulk()` → Brick class + room + property.
3. `timescale.insert_readings()` writes rows to the `readings` hypertable.
4. `afdd-engine/main.py` scheduler tick → `evaluator.evaluate_all()`.
5. `neo4j_client.devices_by_brick_class()` returns target devices; `timescale.window()` returns recent values.
6. `rules/threshold.py` (etc.) returns `faulted=True`.
7. `fault_manager.open_fault()` writes a `Fault` node (dedup); `dispatcher` logs + webhooks.
8. `dashboard/index.html` calls `/dashboard/summary` + `/topology` + `/faults` → the room turns red and the activity log shows the fault.
