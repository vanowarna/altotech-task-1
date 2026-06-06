# AltoTech — Multi-Site AFDD with Brick Schema · Implementation Plan

> Candidate: **Vanodhya Warnasooriya** · Role: Full-Stack (Backend/Infra) · Assessment: Graph DB Edition v2
> Principle: *Detect. Diagnose. Optimize.* — and **design-first, then build**.

This document is the master plan. It is written to be defended in the interview follow-up. Everything is designed to run **at zero cloud cost** on a single laptop via Docker Compose, while the *design* reasons explicitly about scaling to 100+ sites / 1000+ sensors.

---

## 1. Executive Summary

We build a **Multi-Site AFDD (Automated Fault Detection & Diagnostics) platform** that models 3 hotels as a **Brick Schema graph in Neo4j**, ingests high-frequency sensor readings into **TimescaleDB**, and runs a **Brick-aware AFDD engine** that resolves rule targets by graph traversal, evaluates time-windowed conditions, manages a fault lifecycle, and dispatches alerts through a **pluggable channel** (Telegram / webhook / log). A **modern single-page dashboard** (light/dark, mobile-responsive) and the required **Swagger UI** both come up with one `docker compose up`.

**The defining design decision** (explicitly graded): the **graph/time-series boundary**. Topology + semantics (Brick) live in Neo4j; high-volume readings live in TimescaleDB, linked by `device_id`. This is the natural fit and exactly the tradeoff the assessment wants discussed.

---

## 2. Technology Choices & Rationale (cost-conscious, enterprise-scoped)

| Concern | Choice | Why (defense) | Enterprise equivalent |
|---|---|---|---|
| Graph DB | **Neo4j Community** | Most mature tooling, clean labelled-property graph, approachable Cypher, great for live demo (Neo4j Browser). Free, single Docker image. | Neo4j Aura / clustered Enterprise |
| Time-series | **TimescaleDB** | Postgres extension → hypertables, continuous aggregates, SQL. Cleanly separates the high-write path from the graph. Free. | TimescaleDB Cloud / managed Postgres |
| API | **FastAPI** | Async, minimal boilerplate, **auto OpenAPI/Swagger** (a required deliverable), Pydantic validation. | Same, behind API gateway |
| AFDD scheduler | **APScheduler** (in-process) | Zero infra for POC; interval-based rule evaluation. Design documents the swap to a distributed broker. | Celery + Redis / Temporal / cloud cron |
| Alerting | **Pluggable dispatcher**: webhook + log (adapter pattern) | Zero external setup for the demo; adapter seam proves extensibility (Telegram/email/etc. are ~30-line add-ons). | Email/SMS/PagerDuty/MS Teams via queue |
| Dashboard | **Single-page** (HTML + Tailwind + Chart.js) | Modern, minimal, light/dark, mobile-responsive; served statically, boots with compose. | Same SPA behind CDN/auth |
| Orchestration | **Docker Compose** | One-command startup (required). | Kubernetes (bonus manifests included) |
| Language | **Python 3.11** | Matches AltoTech reference stack; best Brick/data ecosystem. | — |

**Cost stance:** every component is free and local. Where an enterprise would pay (managed graph DB, distributed queue, paid alert channels, cloud TS), the design names the upgrade path so the small-scale POC maps cleanly onto the 400-property target.

---

## 3. System Architecture

```
                ┌─────────────────────────────────────────────────────────┐
                │                   Docker Compose network                 │
                │                                                          │
 Edge Simulator │  ┌────────────┐   POST /ingest   ┌──────────────────┐    │
 (3 hotels,     ├─▶│  Ingestion │─────────────────▶│   FastAPI API    │    │
  configurable) │  │   client   │                  │  (ingest/query/  │    │
                │  └────────────┘                  │   rules/faults)  │    │
                │                          ┌────────┤                  │    │
                │   Brick resolution       │        └───────┬──────────┘    │
                │   (graph lookup)         ▼                │ write reading │
                │                  ┌──────────────┐  ┌──────▼───────────┐   │
                │                  │   Neo4j      │  │  TimescaleDB     │   │
                │                  │ (Brick graph:│  │ (readings        │   │
                │                  │  Property/   │  │  hypertable,     │   │
                │                  │  Location/   │  │  keyed by        │   │
                │                  │  Device/Rule/│  │  device_id)      │   │
                │                  │  Fault nodes)│  └──────▲───────────┘   │
                │                  └──────▲───────┘         │ window query  │
                │                         │ traverse targets│               │
                │                  ┌──────┴─────────────────┴───────────┐   │
                │                  │        AFDD Engine                 │   │
                │                  │  scheduler → evaluator → fault mgr │   │
                │                  │            → alert dispatcher      │   │
                │                  └──────┬──────────────────┬──────────┘   │
                │                         │ fault records    │ alerts       │
                │                         ▼                  ▼              │
                │                  ┌──────────────┐   ┌──────────────┐      │
                │   Dashboard ◀────│  Fault API   │   │ Telegram /   │      │
                │   + Swagger UI   │  (counts,    │   │ webhook /log │      │
                │                  │   severity)  │   └──────────────┘      │
                │                  └──────────────┘                         │
                └──────────────────────────────────────────────────────────┘
```

**Data flow:** Edge Simulator → Ingestion API (resolve Brick class + relationships via Neo4j) → store reading in TimescaleDB keyed to the graph Device → AFDD Engine periodically traverses the graph for rule targets, queries TimescaleDB windows, evaluates conditions → creates/resolves Fault nodes in Neo4j → dispatches alerts → Dashboard reads fault/dashboard APIs.

---

## 4. Repository & Module Structure (modular for parallel development)

Each top-level module is independently developable and testable.

```
altotech-task-1/
├── 00-documents/                # provided assessment PDF + sample CSVs (given)
├── README.md                    # one-command startup + overview
├── PROGRESS.md                  # running build log (summaries, updated each phase)
├── docs/
│   ├── PLAN.md                  # this document
│   ├── architecture/            # system overview, component & data-flow diagrams
│   ├── adr/                     # ADR-0001 graph DB, 0002 TS boundary, 0003 alerting, ...
│   ├── brick-schema/            # Brick model, class hierarchy, resolution flow
│   ├── diagrams/                # mermaid/png sources for the GitHub Wiki
│   └── wiki/                    # exported markdown → GitHub Wiki
├── services/
│   ├── api/                     # FastAPI app
│   │   ├── app/ (routers, schemas, deps, main.py, health, metrics)
│   │   └── tests/
│   ├── afdd-engine/             # scheduler, evaluator, fault_manager, dispatcher, rules/
│   │   └── tests/
│   ├── edge-simulator/          # configurable simulator (config.yaml + simulator.py)
│   │   └── tests/
│   └── dashboard/               # single-page UI (index.html, app.js, styles)
├── packages/shared/             # shared lib: brick mapping, db clients, models, config
├── graph/                       # cypher schema, constraints, seed/load scripts
├── deploy/
│   ├── docker-compose.yml       # api + neo4j + timescaledb + simulator + engine + dashboard
│   ├── .env.example             # dev/prod env configs
│   ├── prometheus/              # metrics scrape config (bonus)
│   └── k8s/                     # Kubernetes manifests (bonus)
├── skills/                      # bonus Claude Code SKILL.md (Brick + AFDD)
├── tests/integration/          # end-to-end across services
└── .github/workflows/ci.yml     # lint + unit + integration on PR
```

**Shared package** (`packages/shared`) holds the Brick class mapping, Neo4j/TimescaleDB clients, and Pydantic models so the API, engine, and simulator stay consistent without duplication.

---

## 5. Brick Schema Graph Model (Neo4j)

**Node labels & key properties**

| Label | Purpose | Key properties |
|---|---|---|
| `Property` | Hotel/site | `id, name, timezone, config, created_at` |
| `Location` | Room/zone/floor | `id, name, floor, type` |
| `Device` (`:Point`) | Sensor/meter | `id, device_type, brick_class, unit, metadata` |
| `BrickClass` | Brick ontology type | `uri` (e.g. `brick:Zone_Air_Temperature_Sensor`) |
| `Rule` | AFDD rule config | `id, name, brick_class_target, condition_type, thresholds, duration, severity, enabled, property_overrides` |
| `Fault` | Detected fault | `id, severity, status, detected_at, resolved_at, context` |

**Relationships (Brick-aligned)**

```
(:Property)-[:hasPart]->(:Location)
(:Location)-[:hasPoint]->(:Device)
(:Device)-[:hasLocation]->(:Location)      // inverse for fast resolution
(:Device)-[:rdf_type]->(:BrickClass)        // native Brick typing
(:Device)-[:isPointOf]->(:Equipment)        // where applicable
(:Rule)-[:targets]->(:BrickClass)
(:Fault)-[:detectedOn]->(:Device)
(:Fault)-[:raisedBy]->(:Rule)
```

**Brick class mapping** (per assessment): temperature→`Zone_Air_Temperature_Sensor`, humidity→`Zone_Air_Humidity_Sensor`, co2→`CO2_Sensor`, occupancy→`Occupancy_Sensor`, power→`Electrical_Power_Sensor`.

**Resolution at ingestion** (the key integration point): payload carries only `device_id, datapoint, value, timestamp`. The API does a single Cypher lookup:
```cypher
MATCH (d:Device {id:$id})-[:rdf_type]->(b:BrickClass)
MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
RETURN b.uri AS brick_class, l.name AS location, p.id AS property
```
The resolved Brick context is attached and the reading is written to TimescaleDB. **`brick_class` is never carried on the wire** — it is derived from the graph, exactly as specified.

**Auto-enabling rules:** because a Rule `targets` a `BrickClass` and Devices are typed by `rdf_type` edges, adding a new device of an existing Brick class instantly falls under every matching rule — no code change. Adding a new Brick class + a rule that targets it enables detection across all sites by graph traversal alone.

---

## 6. Graph vs. Time-Series Boundary (ADR-0002 — the headline decision)

- **Graph (Neo4j):** slow-changing topology and semantics — properties, locations, devices, Brick types, rules, faults. Small node count, rich relationships, traversal-heavy reads.
- **Time-series (TimescaleDB):** the firehose — one row per device per ~30–60s. Hypertable `readings(time, device_id, datapoint, value)` partitioned by time, with continuous aggregates for rolling windows.
- **Link:** `device_id` is the join key. Neo4j answers "*which* devices" (by Brick class, location, property); TimescaleDB answers "*what values* over the last N minutes". Neither is forced to do the other's job.
- **Tradeoff defended:** graph DBs are poor at high-volume time-series writes; time-series DBs can't express topology. Splitting plays to both strengths and is how the engine stays fast at 1000+ sensors.

---

## 7. AFDD Engine Design

**Components:** Rule Scheduler (APScheduler, configurable interval) → Condition Evaluator (graph-resolves targets, queries TS windows) → Fault Manager (lifecycle + dedup) → Alert Dispatcher (pluggable).

**Evaluation loop (per rule):**
1. Traverse Neo4j: all Devices whose `rdf_type` = rule's target Brick class (optionally scoped by property).
2. Query TimescaleDB for each device's recent window (e.g. last 15 min).
3. Apply condition logic.
4. If fault met **and** no active fault for (device, rule) → create `Fault` (status=`active`) with context; **dedup** prevents duplicates.
5. If condition cleared **and** active fault exists → resolve it.
6. Structured-log + dispatch alert.

**Fault lifecycle:** `detected → active → acknowledged → resolved`.

**Rules implemented (4 of 3–4 required):**

| Rule | Logic | Default threshold | Target Brick class |
|---|---|---|---|
| Temperature Excursion | value outside setpoint±Δ for X min | > 28°C for 10 min | `Zone_Air_Temperature_Sensor` |
| Sensor Flatline | stddev ≈ 0 over window | 0 variance for 30 min | any sensor |
| Schedule Violation | active outside operating hours | occupancy/power ON after 22:00 | `Occupancy_Sensor` / `Electrical_Power_Sensor` |
| Energy Anomaly | consumption > rolling avg by X% | > 150% of 7-day avg | `Electrical_Power_Sensor` |

**Configurability:** rules are **nodes in the graph** with JSON-ish properties and `property_overrides` (e.g. `hotel_a` threshold 26). New rule *types* are added via a small **rule-evaluator registry** (`condition_type → evaluator fn`) — a plugin seam documented for "new rules without code changes."

---

## 8. API Surface (FastAPI, all under `/api/v1`)

- **Setup (CRUD, minimal):** `POST/GET /properties`, `POST/GET /devices`.
- **Ingestion:** `POST /ingest` (single), `POST /ingest/batch` — validate, resolve Brick via graph, store reading.
- **Query:** `GET /devices/{id}/readings?from&to`, `GET /devices/{id}/latest`, `GET /devices?brick_class=&floor=&property=` (graph traversal).
- **Rules:** `POST/GET/PUT/DELETE /rules`, `PATCH /rules/{id}/enable`.
- **Faults:** `GET /faults?property&severity&status`, `GET /faults/{id}`, `POST /faults/{id}/ack`, `POST /faults/{id}/resolve`, `POST /faults/{id}/notes`.
- **Dashboard data:** `GET /dashboard/summary` (counts by property, severity distribution, recent faults).
- **Ops:** `GET /health`, `GET /metrics` (Prometheus), `/docs` (Swagger).

---

## 9. Dashboard (modern, minimal, presentation-grade)

Single-page app served statically and wired into compose. Modern minimalistic professional style, **light/dark toggle**, **mobile-responsive**. Sections: KPI tiles (active faults, by severity), fault list with filters and ack/resolve actions, severity distribution chart (Chart.js), and an optional **Three.js building/room view** that highlights rooms with active faults. Reads only the public APIs — no business logic in the client. Boots automatically with `docker compose up`.

---

## 10. Deployment, Testing & Docs

- **Docker Compose:** `api`, `neo4j`, `timescaledb`, `edge-simulator`, `afdd-engine`, `dashboard` (+ optional `prometheus`). Healthchecks + `depends_on` ordering. `.env` for dev/prod. One command: `docker compose up`.
- **Bonus:** k8s manifests, Prometheus metrics endpoint, simple load-test notes.
- **Testing:** unit tests per service (rules, Brick resolution, simulator anomalies), integration test for the full ingest→detect→alert path, coverage report. **CI** via GitHub Actions on PRs.
- **Docs / GitHub Wiki:** System Architecture, Flow/Sequence diagrams (ingestion + AFDD cycle), ADRs (graph DB, TS boundary, alerting, scheduler), Brick Schema design. Authored in `docs/` and mirrored to the Wiki.
- **AI-ready + Bonus SKILL.md:** document graph/data/config export for AI rule discovery; ship a Claude Code `SKILL.md` teaching Brick modeling patterns, common Cypher queries, and the rule-config schema so an AI can generate valid rules.

---

## 11. GitHub Workflow

Feature branches per module (`feat/edge-simulator`, `feat/brick-graph`, `feat/afdd-engine`, …), meaningful commits, PRs with descriptions, CI gating. Demonstrates the PR hygiene that is explicitly graded.

---

## 12. Phased Execution Plan (step-by-step after approval)

Mapped to assessment task weights. Each phase ends with a **PROGRESS.md** summary + tests + a commit.

- **Phase 0 — Design-first (docs)** · *prereq, graded as "design-first"*
  ADRs, architecture + data-flow + sequence diagrams, Brick model doc. Repo skeleton + folders.
- **Phase 1 — Foundation (Task 1, 20%)**
  Graph schema + constraints + load script (3 hotels: A=10, B=8+power, C=12). Edge simulator (configurable, realistic anomalies). FastAPI ingestion + TimescaleDB readings + query APIs.
- **Phase 2 — Brick Schema integration (Task 2, 30%)**
  Native Brick typing, resolution-at-ingestion, query-by-Brick-class traversal APIs, Brick design doc, external-integration contracts.
- **Phase 3 — AFDD engine (Task 3, 35%)**
  Scheduler + evaluator + fault manager + dispatcher; 4 rules; rule + fault APIs; pluggable Telegram/webhook/log; scalability + AI-ready doc; **SKILL.md** bonus.
- **Phase 4 — Dashboard + Deployment + Docs (Task 4, 15%)**
  Single-page dashboard (light/dark, mobile, optional 3D). Docker Compose one-command, health checks, structured logging, Swagger, README, Wiki export, k8s/Prometheus bonus.
- **Phase 5 — Verification & demo prep**
  End-to-end run, tests + coverage, screenshots, demo script, interview-defense notes.

---

## 13. Interview-Defense Cheat Sheet (maps to §12 follow-up questions)

- *Why graph DB / why Neo4j?* → buildings are graphs; Brick is RDF; Neo4j = best tooling + demo. §2/§5.
- *Brick model & ingestion resolution?* → typed nodes + `rdf_type`/`hasLocation`; single Cypher lookup; class off the wire. §5.
- *Where do readings live & why?* → TimescaleDB hypertable keyed by `device_id`; graph for topology. §6.
- *How does the engine resolve targets & handle faults?* → traverse Brick class → window query → dedup'd lifecycle → dispatch. §7.
- *Scale to 100+ sites?* → shard rule jobs by property, continuous aggregates, distributed scheduler, graph read replicas. §2/§7.
- *AI tool usage & GitHub workflow?* → AI-assisted build, feature branches + PRs + CI; SKILL.md for AI rule generation. §10/§11.

---

## 14. Progress Tracking

`PROGRESS.md` at repo root is updated at the end of every phase with a **short summary** (what shipped, decisions, next step) to keep context tight and avoid rate limits. Per-phase design notes live under `docs/`. The plan is the single source of truth; deviations are recorded as new ADRs.
