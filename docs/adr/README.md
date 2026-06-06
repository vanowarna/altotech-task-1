# Architecture Decision Records (ADRs)

Each ADR captures one significant technical decision, its context, the options weighed, and the consequences. Written **before implementation** to demonstrate design-first engineering, and to answer the assessment's interview follow-up questions directly.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-graph-database.md) | Use Neo4j Community as the graph database | Accepted |
| [0002](0002-timeseries-boundary.md) | Store high-frequency readings in TimescaleDB, keyed to the graph | Accepted |
| [0003](0003-alerting-dispatcher.md) | Pluggable alert dispatcher (webhook + structured log) | Accepted |
| [0004](0004-afdd-scheduler.md) | In-process APScheduler for rule evaluation (POC) | Accepted |
| [0005](0005-backend-framework.md) | FastAPI for the service layer | Accepted |

Format: Context → Decision → Alternatives → Consequences → Scale path.
