# Flow Charts & Sequence Diagrams

## Ingestion with Brick resolution
```mermaid
sequenceDiagram
  participant E as Edge (sim / csv)
  participant API as Ingestion API
  participant NEO as Neo4j
  participant TS as TimescaleDB
  E->>API: POST /ingest/batch [{device_id, datapoint, value, ts}]
  API->>NEO: bulk resolve -> brick_class, location, property
  NEO-->>API: Brick context per device
  API->>TS: INSERT readings keyed by device_id
  API-->>E: 202 {accepted, rejected}
```
`brick_class` is resolved from the graph, never sent on the wire.

## AFDD evaluation cycle
```mermaid
sequenceDiagram
  participant SCH as Scheduler
  participant EV as Evaluator
  participant NEO as Neo4j
  participant TS as TimescaleDB
  participant FM as Fault Manager
  participant DISP as Dispatcher
  SCH->>EV: tick (every EVAL_INTERVAL_SECONDS)
  EV->>NEO: rule -> target devices by Brick class
  loop per device
    EV->>TS: recent window (+ baseline for energy)
    EV->>EV: evaluate condition
    alt faulted & no open fault
      EV->>FM: open fault (dedup)
      FM->>NEO: CREATE Fault -[:detectedOn]->device, -[:raisedBy]->rule
      FM->>DISP: webhook + structured log
    else cleared
      EV->>FM: resolve open fault
    end
  end
```

## Dashboard read (live 3D console)
```mermaid
sequenceDiagram
  participant UI as Dashboard SPA
  participant API as API
  participant NEO as Neo4j
  participant TS as TimescaleDB
  UI->>API: GET /dashboard/stats, /summary, /topology, /readings, /faults
  API->>NEO: counts, fault aggregates, building topology + per-room status
  API->>TS: ingest rate, latest value per device
  API-->>UI: JSON
  Note over UI: rooms colored by worst fault; hover shows live readings
```

## Fault lifecycle
```mermaid
stateDiagram-v2
  [*] --> detected
  detected --> active
  active --> acknowledged
  acknowledged --> resolved
  active --> resolved
  resolved --> [*]
```
