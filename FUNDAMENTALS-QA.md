# Fundamentals Q&A — interview prep

> Personal prep (git-ignored). Short questions and answers covering the fundamentals a
> reviewer is likely to probe, plus the **enterprise option vs. the POC choice** and why.
> Companion to `docs/interview-defense.md` (which answers the assessment's 8 listed questions).

---

## A. Brick Schema & graph modeling

**Q: What is Brick Schema?**
An open-source **RDF ontology** for buildings — a standard vocabulary of equipment, sensors
(points), and locations and the relationships between them. It makes applications portable
across buildings.

**Q: Why model the building as a graph instead of relational tables?**
Buildings *are* graphs (property → floor → room → device → equipment). Questions like "all
temperature sensors on Floor 2" or "which sensors are in Room 101" are **graph traversals**,
not multi-table joins. Brick is itself a graph, so the graph is its natural home.

**Q: How is a sensor typed?**
Each `Device` node has an `rdf_type` edge to a `BrickClass` node (e.g.
`brick:Zone_Air_Temperature_Sensor`). Typing is data, not a column.

**Q: What does "resolution at ingestion" mean?**
The wire payload carries only `device_id, datapoint, value, timestamp`. At ingestion the API
looks the device up in the graph to attach its Brick class, room, and property. `brick_class`
is therefore **never sent by the sensor** — it's derived from the graph.

**Q: How do new devices/rules avoid code changes?**
A `Rule` `targets` a `BrickClass`; devices are typed by `rdf_type`. Add a device of an existing
class → it's automatically covered by matching rules. Add a class + a rule → detection is
enabled fleet-wide by traversal alone.

---

## B. The storage boundary (the headline)

**Q: Where do high-volume readings live, and why not in the graph?**
In **TimescaleDB**, not Neo4j. Graph DBs are excellent at topology but poor at high-volume
time-series writes; a time-series DB can't express topology. We split by access pattern and
join on `device_id`: Neo4j answers *which* devices, TimescaleDB answers *what values over time*.

**Q: What is TimescaleDB / a hypertable / a continuous aggregate?**
TimescaleDB is a Postgres extension for time-series. A **hypertable** auto-partitions a table by
time (chunks) for fast inserts and range scans. A **continuous aggregate** is an
incrementally-maintained materialized view (e.g. hourly averages) — cheap rolling stats for the
energy rule.

**Q: How do the two stores stay consistent?**
A device must exist in the graph before its readings resolve (ingestion rejects unknown
devices). `device_id` is the foreign key by convention.

---

## C. AFDD engine

**Q: How does the engine work each cycle?**
For each enabled rule: traverse the graph for target devices of its Brick class → query each
device's recent window from TimescaleDB → apply the condition → open or resolve a fault →
dispatch an alert.

**Q: How do you prevent duplicate faults?**
The fault manager creates a fault only `WHERE NOT EXISTS` an open fault for the same
(device, rule). Dedup lives in the database, not process memory — so multiple workers can't
double-open.

**Q: What's the fault lifecycle?**
`detected → active → acknowledged → resolved`. The engine opens/auto-resolves; operators ack/
resolve via the API.

**Q: How are rules configurable without redeploying?**
Rules are **graph nodes** (`condition_type` + `params` + `property_overrides`). New rule
*instances* are created via `POST /rules`. New rule *types* register an evaluator with
`@register("...")` — a lightweight plugin DSL.

**Q: The four rules?**
Temperature excursion (sustained over threshold), sensor flatline (≈ zero variance), schedule
violation (active outside operating hours), energy anomaly (recent avg > rolling baseline by %).

---

## D. Platform / API

**Q: Why FastAPI?**
Async I/O for the ingest path, Pydantic validation at the boundary, and **auto-generated
OpenAPI/Swagger** (a required deliverable) for free.

**Q: Why is the dashboard served by nginx with a proxy?**
nginx serves the static SPA and reverse-proxies `/api` to the API container, so the browser
talks **same-origin** — no CORS complications. (CORS is also enabled on the API as a fallback.)

**Q: How is the system observable / healthy?**
Structured JSON logs everywhere, `/health` + `/ready`, Docker healthchecks for startup ordering,
and Prometheus metrics at `/metrics`.

---

## E. Scaling & operations

**Q: How would this scale to 100+ sites?**
Three axes: shard rule evaluation by `property_id` across distributed workers (engine is
stateless, dedup in DB); keep the graph small (readings aren't in it) and add read replicas;
scale TimescaleDB with chunking/compression/continuous-aggregates and sharding by property/time.

**Q: How is multi-tenancy handled?**
Every node hangs off exactly one `Property`; queries scope by property; rules carry
`property_overrides` for per-site thresholds.

**Q: How would cross-site patterns be found?**
Faults are nodes linked to rules and Brick classes, so cross-site questions are graph
aggregations over the (small) graph + the continuous aggregates.

---

## F. Enterprise option vs. POC choice (and why)

| Area | Enterprise option | POC choice | Why the POC choice |
|---|---|---|---|
| Graph DB | Neo4j Aura / Enterprise cluster; or managed RDF (GraphDB) | **Neo4j Community** | Mature Cypher + browser for the demo; free; same model. Clustering/HA is an ops upgrade, not a code change. |
| Time-series | Timescale Cloud / managed Postgres | **TimescaleDB self-hosted** | Identical engine/features locally at zero cost. |
| Rule scheduling | Celery + Redis, Temporal, or cloud scheduler | **APScheduler in-process** | No broker to run; engine is stateless so the scheduler is a swappable seam. |
| Alert delivery | Message queue → email/SMS/PagerDuty/Teams (durable, retried, fan-out) | **webhook + structured log** | Zero external accounts; adapter pattern shows the extension is ~30 lines. |
| Ingestion transport | Kafka / MQTT broker + stream processor | **HTTP POST /ingest/batch** | Simple, debuggable, fine at POC volume; the API contract is unchanged behind a broker. |
| Orchestration | Kubernetes (HPA, secrets, ingress, TLS) | **Docker Compose** | One-command local startup; k8s manifests provided as the path. |
| AuthN/Z | OAuth2/OIDC + RBAC + per-tenant API keys | **none** | Out of scope for a detection POC; named explicitly. |
| Secrets | Vault / cloud secret manager | **`.env` with defaults** | Simplicity; production path documented. |
| CI/CD | Full pipeline + image registry + staged deploys | **GitHub Actions** (lint, tests, image build) | Demonstrates the workflow without infra. |

**One-liner to say out loud:** *"Every component is the real thing at small scale — the
enterprise versions are operational upgrades (managed hosting, a queue, a distributed
scheduler, k8s), not rewrites, because the boundaries and contracts already assume them."*

---

## G. Likely "gotcha" questions

**Q: Why did the dashboard look sparse at first?**
It's a **fault console** — it shows what's *wrong*. With only a handful of injected anomalies,
few faults is correct. The live KPIs + 3D hover added the "see everything that's flowing" view.

**Q: A test passed but a runtime bug slipped through — how?**
Unit tests cover pure logic; the fault manager only runs against a live Neo4j. I added a
**DB-free regression test** that asserts every `$param` referenced in the fault Cypher is
supplied — it catches that class of bug without a database.

**Q: Why run tests per-service in CI?**
Each service has its own top-level `app` package; a single pytest process across services
collides in `sys.modules`. Running each suite in its own process is the standard fix for a
multi-service repo.

**Q: Where would AI fit?**
The platform exports graph + rules + faults as JSON and ships a Claude Code skill describing the
Brick patterns and rule schema, so an AI can propose valid rules that are validated against live
data — a discover→validate loop.
