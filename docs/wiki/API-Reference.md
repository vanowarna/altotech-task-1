# API Reference (`/api/v1`)

Machine-readable contract: `GET /openapi.json`; interactive: `/docs` (Swagger).

| Area | Endpoint | Purpose |
|---|---|---|
| Ingestion | `POST /ingest` · `POST /ingest/batch` | Receive readings; resolve Brick via graph; store. |
| Data query | `GET /devices/{id}/latest` | Latest reading for a device. |
| | `GET /devices/{id}/readings?from&to` | Time-range readings. |
| | `GET /devices?brick_class=&property=&floor=` | Query devices by Brick class (traversal). |
| Setup | `POST/GET /properties` · `POST /devices` | Minimal graph-node CRUD. |
| Rules | `POST/GET/PUT/DELETE /rules` | Rule CRUD (config as graph nodes). |
| | `PATCH /rules/{id}/enable?enabled=&property=` | Enable/disable globally or per property. |
| Faults | `GET /faults?property&severity&status` | List/filter faults. |
| | `GET /faults/{id}` | Fault details + context. |
| | `POST /faults/{id}/ack` · `/resolve` · `/notes` | Lifecycle actions. |
| Dashboard | `GET /dashboard/summary` | Fault counts by property, severity distribution, recent. |
| | `GET /dashboard/stats` | Device counts, healthy vs faulted, ingest rate. |
| | `GET /dashboard/topology` | Building structure + per-room fault status + device list (3D). |
| | `GET /dashboard/readings` | Latest value per device (live hover panel). |
| Ops | `GET /health` · `/ready` · `/metrics` | Liveness, readiness, Prometheus. |

## Rule config schema (POST /rules)
```json
{
  "name": "High Temperature Alert",
  "brick_class_target": "brick:Zone_Air_Temperature_Sensor",
  "condition_type": "threshold_exceeded",
  "params": { "threshold_value": 28, "comparison": ">", "duration_minutes": 10, "window_minutes": 15 },
  "severity": "warning",
  "enabled": true,
  "property_overrides": { "hotel_a": { "threshold_value": 26 } }
}
```
Condition types: `threshold_exceeded`, `flatline`, `schedule_violation`, `energy_anomaly`.
