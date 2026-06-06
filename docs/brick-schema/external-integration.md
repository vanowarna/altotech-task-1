# External Integration Design

How the AFDD platform integrates with the systems AltoTech runs alongside it —
**analytics dashboards, digital-twin platforms, and third-party BMS** — and the
**API contracts** external consumers use. The unifying idea: because devices are
typed by **Brick class** in the graph, every external contract is keyed on Brick
semantics and is therefore **portable across any property** with no per-building
remapping.

## Integration map

```mermaid
flowchart LR
  subgraph AFDD Platform
    API[FastAPI]
    NEO[(Neo4j Brick graph)]
    TS[(TimescaleDB)]
    DISP{{Alert dispatcher}}
  end
  AN[Analytics dashboard] -->|GET /devices?brick_class=...| API
  AN -->|GET /devices/{id}/readings| API
  DT[Digital twin] -->|graph export / GET topology by Brick| API
  BMS[3rd-party BMS] -->|POST /ingest, webhook faults| API
  DISP -->|fault webhook events| AN
  DISP -->|fault webhook events| BMS
  API --- NEO
  API --- TS
```

## 1. Analytics dashboards
**Need:** equipment discovery by type + time-series for charts and KPIs.
**Contract (already implemented):**
- `GET /api/v1/devices?brick_class=brick:CO2_Sensor&property=hotel_a&floor=2`
  → device list via graph traversal.
- `GET /api/v1/devices/{id}/readings?from=<unix>&to=<unix>` → time-series for plots.
- `GET /api/v1/devices/{id}/latest` → live tiles.
- (Phase 3) `GET /api/v1/dashboard/summary` → fault counts by property, severity distribution.

Because queries are by Brick class, the same dashboard definition ("plot all
`Zone_Air_Temperature_Sensor` on Floor 2") works for any hotel.

## 2. Digital-twin platforms
**Need:** the building topology + semantics as a portable graph to mirror into a twin.
**Contract:**
- **Graph export** — `GET /api/v1/graph/export?property=hotel_a` returns nodes
  (Property/Location/Device with Brick classes) and edges (`hasPart`, `hasPoint`,
  `rdf_type`, `hasLocation`) as JSON. This is a faithful Brick projection a twin can
  ingest directly. *(export endpoint scheduled in Phase 3 AI-ready work; the
  underlying traversal exists today.)*
- Twins subscribe to live values via the per-device reading endpoints above.

Brick is RDF-native, so the export maps 1:1 to a twin's own ontology layer.

## 3. Third-party BMS
**Need:** push raw points in, receive fault events out.
**Contract:**
- **Ingest** — `POST /api/v1/ingest` / `POST /api/v1/ingest/batch`. The BMS sends
  only `device_id, datapoint, value, timestamp`; Brick class is resolved in our
  graph. A BMS integrates by registering its devices once (`POST /api/v1/devices`)
  with a `location_id` and `datapoint`; typing is automatic.
- **Fault webhooks** — the alert dispatcher (ADR-0003) POSTs a JSON fault event to a
  configured URL so a BMS/CMMS can open a work order.

### Fault webhook event contract (outbound)
```json
{
  "event": "fault.detected",
  "fault_id": "f_01H...",
  "rule": "High Temperature Alert",
  "brick_class": "brick:Zone_Air_Temperature_Sensor",
  "device_id": "hotel_a-r101-temperature",
  "property_id": "hotel_a",
  "location": "Room 101",
  "severity": "warning",
  "status": "active",
  "detected_at": 1733500000,
  "context": { "window_minutes": 15, "samples": [29.6, 29.9, 30.1] }
}
```
Event types: `fault.detected`, `fault.resolved`. Delivery is best-effort in the POC;
the scale path routes through a message queue for durability and fan-out.

## Versioning & contracts
All endpoints are under `/api/v1`. The OpenAPI schema at `/openapi.json` is the
machine-readable contract; consumers generate clients from it. Breaking changes ship
under a new version prefix.

## Why Brick makes this clean
A consumer integrates against **Brick classes**, not device IDs or per-hotel tables.
Add a 400th property and existing analytics, twins, and BMS contracts keep working
unchanged — the new building's devices are discoverable the moment they are typed in
the graph.
