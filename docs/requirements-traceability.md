# Requirements Traceability Matrix (RTM)

Every requirement from the assessment PDF (*Multi-Site AFDD Service with Brick Schema Integration — Graph DB Edition v2*) mapped to where it is satisfied. Status updated each phase. This is the checklist we validate against before submission.

Legend: ✅ done · 🟡 in progress · ☐ planned

## Task 1 — Foundation: Edge Simulation + Cloud Infra (20%)

| # | Requirement (PDF) | Where satisfied | Status |
|---|---|---|---|
| 1.1 | Simulate 3 hotels — A: 10 rooms (IAQ+occupancy), B: 8 rooms (+power meters/floor), C: 12 rooms | `deploy/topology.yaml`, `graph/load_topology.py` (verified: A=40, B=34, C=51 devices) | ✅ |
| 1.2 | Each sensor pushes every 30–60s | `services/edge-simulator/config.yaml` (`push_interval_seconds`) | ✅ |
| 1.3 | Realistic fault patterns (stuck sensors, temp spikes, schedule violations) | `services/edge-simulator/generators.py` (4 anomaly kinds, unit-tested) | ✅ |
| 1.4 | Python simulator, configurable (hotel count, rooms, sensor types, interval) | `services/edge-simulator/`, topology-driven | ✅ |
| 1.5 | Pushes to cloud ingestion API | `simulator.py` httpx batch push | ✅ |
| 1.6 | Building modeled as graph (typed nodes + relationships) | `graph/schema.cypher`, `graph/load_topology.py` | ✅ |
| 1.7 | Decide where time-series lives + document tradeoffs | ADR-0002 + `deploy/timescale/init.sql` (hypertable) | ✅ |
| 1.8 | API: Property & Device CRUD (minimal) | `services/api/app/routers/devices.py` | ✅ |
| 1.9 | API: Data ingestion (single + batch), validate, resolve Brick via graph | `services/api/app/routers/ingest.py` (bulk resolve) | ✅ |
| 1.10 | API: Data query — latest + time-range by device | `services/api/app/routers/query.py` | ✅ |
| 1.11 | Graph schema / data-model diagram + load scripts | `docs/brick-schema/`, `graph/schema.cypher`, `graph/load_topology.py` | ✅ |
| 1.12 | Design doc: graph model decisions + time-series location | ADR-0001, ADR-0002, brick-model.md | ✅ |

## Task 2 — Brick Schema Graph Modeling & Integration (30%)

| # | Requirement | Where | Status |
|---|---|---|---|
| 2.1 | Brick modeled natively (classes=nodes, relationships=edges) | `graph/load_topology.py` (BrickClass nodes + rdf_type edges) | ✅ |
| 2.2 | Resolution at ingestion (lookup brick_class + relationships) | `ingest.py` + `neo4j_client.resolve_devices_bulk` | ✅ |
| 2.3 | brick_class resolved from graph, NOT carried on wire | `models.Reading` (no brick_class field) + ingest resolver | ✅ |
| 2.4 | Brick class mapping (temp/humidity/co2/occupancy/power) | `packages/shared/afdd_shared/brick.py` (unit-tested) | ✅ |
| 2.5 | Device registry as Brick-typed nodes with relationships | `graph/load_topology.py` | ✅ |
| 2.6 | API: query devices by Brick class via traversal (+floor/property) | `devices.py` `GET /devices`, `neo4j_client.devices_by_brick_class` | ✅ |
| 2.7 | Doc: Brick concepts + why graph fits | brick-model.md | ✅ |
| 2.8 | Doc: class hierarchy + relationships as edges | brick-model.md | ✅ |
| 2.9 | Doc: how rules target Brick classes via traversal | brick-model.md, AFDD doc | ✅ (design) |
| 2.10 | Doc: how new classes/nodes auto-enable rules | brick-model.md | ✅ |
| 2.11 | External integration design (analytics/digital twin/3rd-party BMS) + API contracts | `docs/brick-schema/external-integration.md` (contracts + fault webhook schema) | ✅ |

## Task 3 — Multi-Site AFDD Engine (35%)

| # | Requirement | Where | Status |
|---|---|---|---|
| 3.1 | Rule Scheduler (configurable interval) | `services/afdd-engine` scheduler, ADR-0004 | ☐ |
| 3.2 | Condition Evaluator (graph-resolve targets, time-windowed queries) | engine evaluator | ☐ |
| 3.3 | Fault Manager (create/update/resolve, prevent duplicates) | engine fault_manager | ☐ |
| 3.4 | Alert Dispatcher (webhook/log/queue) | engine dispatcher, ADR-0003 | ☐ |
| 3.5 | Implement 3–4 rules: temp excursion, flatline, schedule violation, energy anomaly | engine `rules/` | ☐ |
| 3.6 | Fault record links rule+device (edges), severity, status, detected_at, context | Fault node model | ✅ (design) |
| 3.7 | Prevent duplicate faults (same device+rule) | fault_manager dedup | ☐ |
| 3.8 | Structured logging of fault events | engine logging | ☐ |
| 3.9 | Fault lifecycle: detected→active→acknowledged→resolved | data-flow.md §3 | ✅ (design) |
| 3.10 | Rules configurable, stored as graph nodes (+property_overrides) | Rule node, brick-model.md | ✅ (design) |
| 3.11 | API: Rule management (CRUD, enable/disable per property) | `services/api` rules router | ☐ |
| 3.12 | API: Fault queries (list active, filter by property/severity/status, details+context) | faults router | ☐ |
| 3.13 | API: Fault actions (ack, resolve, notes) | faults router | ☐ |
| 3.14 | API: Dashboard data (counts by property, severity distribution, recent) | dashboard router | ☐ |
| 3.15 | Scalability doc (100+ sites, partitioning, query perf) | `docs/architecture/scalability.md` | ☐ |
| 3.16 | New rule types without code changes (DSL/plugin) | evaluator registry + doc | ☐ |
| 3.17 | Cross-site pattern detection (aggregated graph analytics) | scalability.md | ☐ |
| 3.18 | AI-ready: export graph/data/configs for AI; format for AI rule suggestions; cross-site learnings | `docs/architecture/ai-ready.md` | ☐ |
| 3.19 | **Bonus** Claude Code SKILL.md (Brick patterns, queries, rule config) | `skills/SKILL.md` | ☐ |

## Task 4 — Deployment & Documentation (15%)

| # | Requirement | Where | Status |
|---|---|---|---|
| 4.1 | Docker Compose (api + graph + TS + simulator + engine) | `deploy/docker-compose.yml` | ☐ |
| 4.2 | Environment configs (dev/prod) | `deploy/.env.example` | ☐ |
| 4.3 | Health check endpoints | `/health` | ☐ |
| 4.4 | Structured logging | shared logging config | ☐ |
| 4.5 | OpenAPI/Swagger UI | FastAPI `/docs` | ☐ |
| 4.6 | README for one-command startup | `README.md` | ☐ |
| 4.7 | **Bonus** Kubernetes manifests | `deploy/k8s/` | ☐ |
| 4.8 | **Bonus** Prometheus metrics endpoint | `/metrics` | ☐ |
| 4.9 | **Bonus** Load test results | `tests/load/` | ☐ |

## Cross-cutting deliverables

| # | Requirement | Where | Status |
|---|---|---|---|
| X.1 | Working prototype, one-command Docker Compose | `deploy/` | ☐ |
| X.2 | GitHub repository (code + tests + docs) | repo | 🟡 |
| X.3 | GitHub Wiki (architecture, flow charts, sequence diagrams, ADRs, Brick design) | `docs/wiki/` export | 🟡 |
| X.4 | Unit + integration tests, coverage | 15 unit tests passing (topology, brick, generators, ingest); integration suite in Phase 5 | 🟡 |
| X.5 | CI pipeline | `.github/workflows/ci.yml` | ☐ |
| X.6 | Design-first evidence (docs before code) | `docs/` (this phase) | ✅ |
| X.7 | GitHub workflow (feature branches, meaningful commits, PRs) | git history | ☐ |
| X.8 | Dashboard: modern, minimal, light/dark, mobile-responsive | `services/dashboard` | ☐ |
