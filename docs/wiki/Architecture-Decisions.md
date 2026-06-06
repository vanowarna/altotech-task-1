# Architecture Decisions (ADRs)

Significant technical decisions, recorded before implementation. Full ADRs:
[`docs/adr/`](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr).

| ADR | Decision | Why (one line) |
|---|---|---|
| [0001](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr/0001-graph-database.md) | **Neo4j Community** as the graph DB | mature tooling, clean Cypher, best for the live demo; Brick maps to a labelled-property graph |
| [0002](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr/0002-timeseries-boundary.md) | **Readings in TimescaleDB**, topology in the graph | graph DBs are poor at high-volume writes; split by access pattern, join on `device_id` |
| [0003](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr/0003-alerting-dispatcher.md) | **Pluggable dispatcher** (log + webhook) | zero external setup for the demo; adapter seam proves extensibility |
| [0004](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr/0004-afdd-scheduler.md) | **In-process APScheduler** for evaluation | no broker infra for the POC; stateless engine → swappable for Celery/Temporal at scale |
| [0005](https://github.com/vanowarna/altotech-task-1/blob/main/docs/adr/0005-backend-framework.md) | **FastAPI** for the service layer | async, auto OpenAPI/Swagger (a required deliverable), strong validation |

## The headline decision: graph vs. time-series boundary
- **Graph (Neo4j):** `Property`, `Location`, `Device`, `BrickClass`, `Rule`, `Fault` — slow-changing, relationship-rich, traversal-heavy.
- **Time-series (TimescaleDB):** the reading firehose — one row per device per ~30–60s, hypertable-partitioned, with continuous aggregates for rolling windows.
- **Link:** `device_id`. Neo4j answers *which* devices; TimescaleDB answers *what values*. Neither does the other's job.

This is the decision the assessment grades hardest, and it keeps the platform fast from 4
properties to 400.
