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
| 3 | AFDD engine + rules + APIs + SKILL.md (Task 3) | ☐ |
| 4 | Dashboard + deployment + docs (Task 4) | ☐ |
| 5 | Verification + demo prep | ☐ |

## Log
- **2026-06-06 · Phase 2 done** — Wrapped Brick integration. Wrote `docs/brick-schema/external-integration.md` (analytics / digital-twin / 3rd-party BMS contracts + outbound fault-webhook event schema + graph-export contract). Added 4 ingestion/resolution unit tests with in-memory fakes (numeric + occupancy coercion, unknown-device rejection, brick_class-from-graph-not-payload). **Tests: 15/15 pass.** Task 2 fully ✅ in RTM. Next: Phase 3 — AFDD engine (scheduler, evaluator, fault manager, dispatcher, 4 rules, rule/fault APIs, SKILL.md).
- **2026-06-06 · Phase 1 done** — Built the foundation. **Shared lib** (`packages/shared/afdd_shared`): Brick mapping, topology builder, Pydantic models, env config, JSON logging, async Neo4j + TimescaleDB clients (incl. bulk device resolution). **Graph**: `schema.cypher` (constraints/indexes) + `load_topology.py` (idempotent MERGE loader). **TimescaleDB**: `init.sql` hypertable + hourly continuous aggregate. **Simulator**: pure `generators.py` (diurnal values + 4 anomaly kinds) + `simulator.py` (backfill + live batch push), `config.yaml`. **API** (FastAPI): ingest single/batch with graph Brick resolution, data query (latest/range), property+device CRUD, query-by-Brick-class traversal, health/ready, /metrics. Dockerfiles for api + simulator. **Tests: 11/11 pass** (topology, brick mapping, generators). Verified topology = A:40 / B:34 / C:51 = 125 devices. Next: Phase 2 wrap (external integration doc + resolution tests), then Phase 3 AFDD engine.
- **2026-06-06 · Phase 0 done** — Repo skeleton created (services/, packages/shared, graph/, deploy/, docs/, skills/, tests/). Wrote 5 ADRs (graph DB, TS boundary, alerting, scheduler, framework), system-overview + sequence diagrams (mermaid), Brick model doc, and a full Requirements Traceability Matrix mapping every PDF requirement to its home. Plan approved; Telegram + Three.js dropped per user. Next: Phase 1 foundation.
- **2026-06-06** — Read assessment + sample data. Confirmed stack. Wrote `docs/PLAN.md`.

## RTM
Validation checklist lives in `docs/requirements-traceability.md` — updated each phase.
