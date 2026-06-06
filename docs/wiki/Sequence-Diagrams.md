# Flow Charts & Sequence Diagrams

Full detail: [`docs/architecture/data-flow.md`](../architecture/data-flow.md).

## Ingestion with Brick resolution
```mermaid
sequenceDiagram
  participant SIM as Edge Simulator
  participant API as Ingestion API
  participant NEO as Neo4j
  participant TS as TimescaleDB
  SIM->>API: POST /ingest { device_id, datapoint, value, timestamp }
  API->>NEO: resolve device → brick_class, location, property
  NEO-->>API: brick context
  API->>TS: INSERT reading keyed by device_id
  API-->>SIM: 202 Accepted
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
  SCH->>EV: tick (every N min) for rule R
  EV->>NEO: targets = devices of R's Brick class
  loop per device
    EV->>TS: recent window readings
    EV->>EV: apply condition
    alt faulted & no active fault
      EV->>FM: open fault (dedup)
      FM->>NEO: CREATE Fault -[:detectedOn]->device, -[:raisedBy]->rule
      FM->>DISP: log + webhook
    else cleared
      EV->>FM: resolve active fault
    end
  end
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
