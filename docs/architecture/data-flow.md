# Sequence Diagrams — Key Operations

## 1. Ingestion with Brick resolution

```mermaid
sequenceDiagram
  participant SIM as Edge Simulator
  participant API as Ingestion API
  participant NEO as Neo4j (graph)
  participant TS as TimescaleDB
  SIM->>API: POST /ingest { device_id, datapoint, value, timestamp }
  API->>API: validate payload (Pydantic)
  API->>NEO: MATCH (d:Device{id})-[:rdf_type]->(b:BrickClass)<br/>(d)-[:hasLocation]->(l)<-[:hasPart]-(p)
  NEO-->>API: brick_class, location, property
  alt device unknown
    API-->>SIM: 404 unknown device
  else resolved
    API->>TS: INSERT reading(time, device_id, datapoint, value)
    API-->>SIM: 202 Accepted { brick_class, location }
  end
```

Note: `brick_class` is **never** sent by the simulator — it is resolved from the graph at ingestion.

## 2. AFDD evaluation cycle

```mermaid
sequenceDiagram
  participant SCH as Scheduler (APScheduler)
  participant EV as Condition Evaluator
  participant NEO as Neo4j
  participant TS as TimescaleDB
  participant FM as Fault Manager
  participant DISP as Dispatcher
  SCH->>EV: tick (every N min) for rule R
  EV->>NEO: MATCH (r:Rule{id:R})-[:targets]->(b)<-[:rdf_type]-(d:Device)<br/>(optional property scope)
  NEO-->>EV: target device_ids (+ thresholds, overrides)
  loop per device
    EV->>TS: SELECT readings WHERE device_id AND time > now-window
    TS-->>EV: recent readings
    EV->>EV: apply condition (threshold / variance / schedule / rolling-avg)
    alt condition met
      EV->>FM: report fault(device, rule, context)
      FM->>NEO: MATCH active Fault for (device,rule)?
      alt no active fault
        FM->>NEO: CREATE (:Fault{status:active})-[:detectedOn]->(d), -[:raisedBy]->(r)
        FM->>DISP: dispatch(fault)
        DISP->>DISP: structured log + webhook POST
      else duplicate
        FM-->>EV: skip (dedup)
      end
    else condition cleared
      EV->>FM: clear(device, rule)
      FM->>NEO: SET active Fault.status = resolved, resolved_at
    end
  end
```

## 3. Fault lifecycle

```mermaid
stateDiagram-v2
  [*] --> detected: condition first met
  detected --> active: persisted, alert sent
  active --> acknowledged: operator action (POST /faults/{id}/ack)
  acknowledged --> resolved: condition cleared or manual close
  active --> resolved: condition cleared
  resolved --> [*]
```
