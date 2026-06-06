# Brick Schema Graph Model

How the Brick ontology maps to our Neo4j labelled-property graph, and how semantics are resolved at ingestion.

## Why Brick + a graph
[Brick Schema](https://brickschema.org/) is an open RDF ontology describing building equipment, points, and their relationships. It standardizes vocabulary so applications are portable across buildings, equipment is discoverable by type ("find all AHUs"), and relationships are queryable ("which sensors are in Room 101"). Because Brick is already a graph, a graph DB is its natural home: **Brick classes → node types, Brick relationships → edges.**

## Node labels

| Label | Brick role | Key properties |
|---|---|---|
| `Property` | site | `id, name, timezone, config, created_at` |
| `Location` | room/zone/floor | `id, name, floor, type` |
| `Device` (also `:Point`) | sensor/meter point | `id, device_type, brick_class, unit, metadata` |
| `BrickClass` | Brick ontology class | `uri` (e.g. `brick:Zone_Air_Temperature_Sensor`) |
| `Rule` | AFDD rule config | `id, name, brick_class_target, condition_type, params(json), severity, enabled, property_overrides(json)` |
| `Fault` | detected fault | `id, severity, status, detected_at, resolved_at, context(json)` |

## Relationships (Brick-aligned)

| Edge | Meaning |
|---|---|
| `(:Property)-[:hasPart]->(:Location)` | site contains location |
| `(:Location)-[:hasPoint]->(:Device)` | location exposes a point |
| `(:Device)-[:hasLocation]->(:Location)` | inverse, for fast resolution |
| `(:Device)-[:rdf_type]->(:BrickClass)` | **native Brick typing** |
| `(:Device)-[:isPointOf]->(:Equipment)` | point belongs to equipment (where modeled) |
| `(:Rule)-[:targets]->(:BrickClass)` | rule applies to all devices of a class |
| `(:Fault)-[:detectedOn]->(:Device)` | fault localized to a device |
| `(:Fault)-[:raisedBy]->(:Rule)` | provenance of the fault |

## Brick class mapping (sensor type → class)

| Sensor type | Brick class | Unit |
|---|---|---|
| temperature | `brick:Zone_Air_Temperature_Sensor` | °C |
| humidity | `brick:Zone_Air_Humidity_Sensor` | %RH |
| co2 | `brick:CO2_Sensor` | ppm |
| occupancy | `brick:Occupancy_Sensor` | state |
| power | `brick:Electrical_Power_Sensor` | kW |

This mapping is the single source of truth, kept in `packages/shared` and reused by the simulator, the graph loader, and the ingestion resolver.

## Resolution at ingestion (the integration point)
Incoming payload carries only `device_id, datapoint, value, timestamp`. The class is derived from the graph:

```cypher
MATCH (d:Device {id: $device_id})-[:rdf_type]->(b:BrickClass)
MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
RETURN b.uri AS brick_class, l.name AS location, p.id AS property_id
```

`d.id` is uniquely constrained → O(1) lookup. The resolved context travels with the reading into TimescaleDB.

## Query devices by Brick class (traversal, not joins)

```cypher
// all temperature sensors on Floor 2 of a property
MATCH (p:Property {id:$pid})-[:hasPart]->(l:Location {floor:2})-[:hasPoint]->(d:Device)
MATCH (d)-[:rdf_type]->(:BrickClass {uri:"brick:Zone_Air_Temperature_Sensor"})
RETURN d.id
```

## How new classes/devices auto-enable rules
A `Rule` targets a `BrickClass`; Devices are typed by `rdf_type`. Therefore:
- Adding a **new device** of an existing class → immediately covered by every rule targeting that class. No code change.
- Adding a **new Brick class + a rule** that targets it → detection is enabled across all sites by traversal alone. No code change.

This is the payoff of modeling semantics natively as a graph rather than as bolted-on tags.

## External integration (contracts)
External consumers (analytics dashboards, digital twins, third-party BMS) query the graph by Brick class via the API:
- `GET /api/v1/devices?brick_class=brick:CO2_Sensor&property=hotel_a&floor=2` → device list
- `GET /api/v1/devices/{id}/latest` and `/readings?from&to` → values
- Faults stream via `GET /api/v1/faults` (filterable) and the webhook dispatcher.

Brick typing makes these contracts portable: a digital twin keyed on Brick classes works against any property without per-building remapping.
