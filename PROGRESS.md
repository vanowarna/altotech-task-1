# Build Progress — Multi-Site AFDD (Brick Schema, Graph DB Edition)

Short rolling log. Updated at the end of every phase to keep context tight.

## Decisions locked
- Graph DB: **Neo4j Community** (Brick graph) + **TimescaleDB** (time-series)
- Backend: **FastAPI**
- Alerting: pluggable **webhook + log** dispatcher (Telegram dropped; trivially re-addable via adapter)
- Dashboard: modern single-page, light/dark, mobile-responsive, **Chart.js (no Three.js)**; boots with Docker Compose
- Real-world target: design must run on actual data, scale to 100+ sites

## Status
| Phase | Scope | State |
|---|---|---|
| 0 | Design-first docs + repo skeleton | ✅ done |
| 1 | Foundation: graph model + simulator + ingestion API (Task 1) | ✅ done |
| 2 | Brick Schema integration + resolution (Task 2) | ✅ done |
| 3 | AFDD engine + rules + APIs + SKILL.md (Task 3) | ✅ done |
| 4 | Dashboard + deployment + docs (Task 4) | ✅ done |
| 5 | Verification + demo prep | ✅ done |

## Log
- **2026-06-06 · Phase 5 done — BUILD COMPLETE** — Verification + demo prep. Added **CI** (`.github/workflows/ci.yml`: compile-lint + 24 unit tests + coverage + builds all 5 images). **Integration smoke test** (`tests/integration/smoke_test.py` + README): live E2E against a running stack — readiness, 3 properties, Brick traversal, ingest+resolve, unknown-device rejection, rules seeded, faults detected (polls for an eval cycle), ack/resolve, dashboard shape. **Demo script** (`docs/DEMO.md`) and **interview-defense notes** (`docs/interview-defense.md`, all 8 Section-12 questions). Final test run: **24/24 unit pass**, coverage on pure logic strong (brick 100%, topology 94%). RTM: all 4 tasks ✅; only optional load-test (4.9) deferred. Sandbox has no Docker, so live E2E is run by the user via `docker compose up` + smoke test. **All phases complete.**
- **2026-06-06 · Phase 4 done** — Dashboard + deployment + docs. **Dashboard** (`services/dashboard`): modern single-page Fault Console — light/dark toggle (persisted), mobile-responsive, Chart.js severity doughnut + per-property bar, filterable fault table with ack/resolve, 15s auto-refresh; served by nginx which reverse-proxies `/api` to FastAPI (same-origin, no CORS pain). **Compose** (`deploy/docker-compose.yml`): 7 services (neo4j, timescaledb, graph-loader init job, api, afdd-engine, edge-simulator, dashboard) with healthchecks + `service_healthy`/`service_completed_successfully` ordering; `.env.example` for dev/prod. Added **CORS** to API. **Bonus**: k8s manifests (`deploy/k8s`), Prometheus scrape config, `/metrics`. **README** with one-command startup + URLs. **GitHub Wiki** export (`docs/wiki`): Home + System Architecture, Sequence Diagrams, ADRs, Brick Schema Design. Validated all YAML parses, dashboard HTML well-formed, anomaly binding correct (energy live-only, others throughout). Fixed a simulator config.yaml YAML error (seq/map mix) and a mount null-byte via direct shell write. Tasks 1–4 ✅. Next: Phase 5 — bring the stack up end-to-end, integration test, screenshots, demo script.
- **2026-06-06 · Phase 3 done** — Built the AFDD engine. **Engine** (`services/afdd-engine`): APScheduler loop (`main.py`), `evaluator.py` orchestrator (graph-resolve targets → window query → evaluate → open/resolve fault → dispatch), `fault_manager.py` (lifecycle + `WHERE NOT EXISTS` dedup), pluggable `dispatcher.py` (Log + Webhook adapters), `seed.py` (idempotent default rules). **4 rule evaluators** via `@register` plugin registry: threshold, flatline, schedule, energy — all pure + 9 unit tests. **APIs** added: rules CRUD + enable/disable-per-property, faults list/get/ack/resolve/notes, dashboard summary. **Shared** `rules.py` (condition-type vocab + DEFAULT_RULES). **Docs**: scalability.md (100+ sites, plugin DSL, cross-site analytics), ai-ready.md (graph/rule export for AI). **Bonus** `skills/SKILL.md` (Brick patterns + Cypher + rule-config schema). Simulator updated so energy anomalies are recent-only (clean baseline). **Tests: 24/24 pass.** Note: hit a mount-sync quirk (bash saw truncated copies of freshly-edited files); re-wrote affected files wholesale — user-facing files verified correct. Tasks 1–3 (85%) now ✅. Next: Phase 4 dashboard + Docker Compose + docs.
- **2026-06-06 · Phase 2 done** — Wrapped Brick integration. Wrote `docs/brick-schema/external-integration.md` (analytics / digital-twin / 3rd-party BMS contracts + outbound fault-webhook event schema + graph-export contract). Added 4 ingestion/resolution unit tests with in-memory fakes (numeric + occupancy coercion, unknown-device rejection, brick_class-from-graph-not-payload). **Tests: 15/15 pass.** Task 2 fully ✅ in RTM. Next: Phase 3 — AFDD engine (scheduler, evaluator, fault manager, dispatcher, 4 rules, rule/fault APIs, SKILL.md).
- **2026-06-06 · Phase 1 done** — Built the foundation. **Shared lib** (`packages/shared/afdd_shared`): Brick mapping, topology builder, Pydantic models, env config, JSON logging, async Neo4j + TimescaleDB clients (incl. bulk device resolution). **Graph**: `schema.cypher` (constraints/indexes) + `load_topology.py` (idempotent MERGE loader). **TimescaleDB**: `init.sql` hypertable + hourly continuous aggregate. **Simulator**: pure `generators.py` (diurnal values + 4 anomaly kinds) + `simulator.py` (backfill + live batch push), `config.yaml`. **API** (FastAPI): ingest single/batch with graph Brick resolution, data query (latest/range), property+device CRUD, query-by-Brick-class traversal, health/ready, /metrics. Dockerfiles for api + simulator. **Tests: 11/11 pass** (topology, brick mapping, generators). Verified topology = A:40 / B:34 / C:51 = 125 devices. Next: Phase 2 wrap (external integration doc + resolution tests), then Phase 3 AFDD engine.
- **2026-06-06 · Phase 0 done** — Repo skeleton created (services/, packages/shared, graph/, deploy/, docs/, skills/, tests/). Wrote 5 ADRs (graph DB, TS boundary, alerting, scheduler, framework), system-overview + sequence diagrams (mermaid), Brick model doc, and a full Requirements Traceability Matrix mapping every PDF requirement to its home. Plan approved; Telegram + Three.js dropped per user. Next: Phase 1 foundation.
- **2026-06-06** — Read assessment + sample data. Confirmed stack. Wrote `docs/PLAN.md`.

## RTM
Validation checklist lives in `docs/requirements-traceability.md` — updated each phase.
