# Interview Defense Notes

Prepared answers to the assessment's Section 12 follow-up questions. Each maps to the
implementation and the relevant doc.

### 1. "Why a graph database, and why Neo4j over the alternatives?"
Buildings *are* graphs (property → location → device → equipment) and Brick Schema is
an RDF graph ontology. Modeling natively means "all AHUs on Floor 2" or "sensors in
Room 101" are traversals, not multi-table joins. I chose **Neo4j Community** for the
most mature tooling, clean Cypher, and a graph browser that makes the model tangible in
a demo. I considered **Apache AGE** (graph + Timescale in one Postgres — elegant but
younger tooling) and **RDF/SPARQL** (truest Brick fit but steepest curve, weak
time-series). See [ADR-0001](adr/0001-graph-database.md).

### 2. "Walk through your Brick model. How does resolution work at ingestion?"
Devices are `:Device` nodes typed by `-[:rdf_type]->(:BrickClass)` and located via
`-[:hasLocation]->(:Location)<-[:hasPart]-(:Property)`. The wire payload is only
`device_id, datapoint, value, timestamp` — **no brick_class**. At ingestion a single
bulk Cypher lookup resolves class + location + property for all devices in the batch,
then the reading is written to TimescaleDB with that context. See
[brick-model](brick-schema/brick-model.md) and `services/api/app/routers/ingest.py`.

### 3. "Where do high-volume readings live, and what drove that boundary?"
TimescaleDB, in a hypertable keyed by `device_id` (the join back to the graph). Graph
DBs are poor at high-volume time-series writes; time-series DBs can't express topology.
I split by access pattern: the graph answers *which* devices, Timescale answers *what
values* over a window. Continuous aggregates back the rolling-average rules. This is
the headline decision — [ADR-0002](adr/0002-timeseries-boundary.md).

### 4. "How does the engine resolve rule targets and evaluate? What happens on a fault?"
Each rule `-[:targets]->(:BrickClass)`. The evaluator traverses to all devices of that
class (optionally property-scoped), pulls each device's recent Timescale window (plus a
baseline for energy), and applies the registered evaluator. On a fault it creates a
`:Fault` linked by `detectedOn`/`raisedBy`, **deduped** via `WHERE NOT EXISTS` so the
same device+rule never double-opens; it logs structured JSON and dispatches to the
webhook/log adapters. When the condition clears, the open fault is resolved. See
`afdd-engine/app/{evaluator,fault_manager}.py`.

### 5. "How would you scale to 100 sites? Where are the bottlenecks?"
Three independent axes: **job distribution** (shard evaluation by `property_id` across
Celery/Temporal workers — the engine is stateless, dedup lives in the graph),
**graph queries** (the graph stays small because readings aren't in it; add read
replicas, scope by property), **time-series** (hypertable chunking + compression +
continuous aggregates, shard by property/time). See
[scalability](architecture/scalability.md).

### 6. "Show how you used AI tools. What worked well?"
AI-assisted development throughout (scaffolding services, Cypher, tests). I also made
the system *itself* AI-ready: it exports graph + rules + faults as JSON, and ships a
Claude Code `skills/SKILL.md` that teaches the Brick patterns, common Cypher, and the
rule-config schema so an AI can generate valid rules — closing a discover→validate loop.
See [ai-ready](architecture/ai-ready.md).

### 7. "Walk through your GitHub workflow and testing."
Design-first (ADRs + diagrams before code), modular services for parallel work, feature
branches → PRs → CI (`.github/workflows/ci.yml` runs compile-lint + 24 unit tests +
image builds). Unit tests cover pure logic (topology, Brick mapping, anomalies,
ingestion resolution, all 4 rule evaluators); a live `tests/integration/smoke_test.py`
verifies the full pipeline. A [requirements traceability matrix](requirements-traceability.md)
maps every assessment requirement to where it's met.

### 8. "What would you do differently with more time?"
Swap APScheduler for a distributed scheduler and shard by property; add a message queue
in front of alerting for durability/fan-out; persistent fault notes/audit and RBAC on
the APIs; richer rule DSL (composite conditions, hysteresis); load tests and SLOs; and a
proper Brick ontology import (RDF) to validate classes against the official vocabulary.

---

## One-line cheat sheet
Graph for topology + Brick semantics (Neo4j), hypertable for readings (TimescaleDB),
joined by `device_id`; Brick resolved at ingestion; engine traverses targets → windows
→ deduped fault lifecycle → pluggable alerts; rules are data + a plugin registry;
scales by property sharding; AI-ready via JSON export + SKILL.md.
