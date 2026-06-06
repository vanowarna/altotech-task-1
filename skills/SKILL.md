---
name: brick-afdd
description: >-
  Work with the AltoTech Multi-Site AFDD platform — model building equipment as
  Brick Schema graph nodes in Neo4j, write Cypher to query sensors by Brick class
  and location, and author valid AFDD rule configurations. Use when creating or
  editing Brick graph topology, querying devices/faults, or generating AFDD rule
  JSON for the rules API.
---

# Brick Schema & AFDD Skill

This skill teaches an AI to understand and extend the Multi-Site AFDD platform:
how buildings are modeled as a Brick graph, how to query that graph, and how to
write valid AFDD rule configurations that the engine will execute.

## 1. Brick graph modeling patterns

Buildings are graphs. Model them as typed nodes connected by Brick relationships.

**Node labels**
- `Property` — a site/hotel. Props: `id, name, timezone`.
- `Location` — room/zone/floor. Props: `id, name, floor, type`.
- `Device` (also `:Point`) — one measurement point. Props: `id, datapoint, brick_class, unit`.
- `BrickClass` — a Brick ontology class. Props: `uri` (e.g. `brick:CO2_Sensor`).
- `Rule` — an AFDD rule (configuration as data).
- `Fault` — a detected fault event.

**Relationships (edges)**
```
(:Property)-[:hasPart]->(:Location)
(:Location)-[:hasPoint]->(:Device)
(:Device)-[:hasLocation]->(:Location)
(:Device)-[:rdf_type]->(:BrickClass)      // native Brick typing
(:Rule)-[:targets]->(:BrickClass)
(:Fault)-[:detectedOn]->(:Device)
(:Fault)-[:raisedBy]->(:Rule)
```

**Sensor type → Brick class (the canonical mapping)**

| datapoint | brick_class |
|---|---|
| temperature | `brick:Zone_Air_Temperature_Sensor` |
| humidity | `brick:Zone_Air_Humidity_Sensor` |
| co2 | `brick:CO2_Sensor` |
| occupancy | `brick:Occupancy_Sensor` |
| power | `brick:Electrical_Power_Sensor` |

Rule: one Device = one point = one Brick class. `brick_class` is resolved from the
graph at ingestion; readings on the wire carry only `device_id, datapoint, value,
timestamp`.

## 2. Common Brick queries (Cypher)

Resolve a device at ingestion:
```cypher
MATCH (d:Device {id:$id})-[:rdf_type]->(b:BrickClass)
MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
RETURN b.uri AS brick_class, l.name AS location, p.id AS property_id
```

All temperature sensors on Floor 2 of a property:
```cypher
MATCH (p:Property {id:$pid})-[:hasPart]->(l:Location {floor:2})-[:hasPoint]->(d:Device)
MATCH (d)-[:rdf_type]->(:BrickClass {uri:"brick:Zone_Air_Temperature_Sensor"})
RETURN d.id
```

Every device a rule targets (across all sites):
```cypher
MATCH (r:Rule {id:$rid})-[:targets]->(:BrickClass)<-[:rdf_type]-(d:Device)
RETURN d.id, d.brick_class
```

Active faults by property:
```cypher
MATCH (f:Fault)-[:detectedOn]->(d:Device)-[:hasLocation]->(:Location)<-[:hasPart]-(p:Property)
WHERE f.status IN ['detected','active','acknowledged']
RETURN p.id, count(f) AS active ORDER BY active DESC
```

## 3. AFDD rule configuration

A rule is JSON `POST`ed to `/api/v1/rules`. Pick a `condition_type`, set its `params`,
and target a Brick class. Adding a rule never requires code changes.

**Condition types & params**
- `threshold_exceeded` — `threshold_value`, `comparison` (`>`|`<`), `duration_minutes`, `window_minutes`
- `flatline` — `window_minutes`, `min_stddev`, `min_samples`
- `schedule_violation` — `operating_start` (HH:MM), `operating_end`, `window_minutes`, `on_value`
- `energy_anomaly` — `pct_above`, `baseline_days`, `window_minutes`

**Valid rule example**
```json
{
  "name": "High Temperature Alert",
  "brick_class_target": "brick:Zone_Air_Temperature_Sensor",
  "condition_type": "threshold_exceeded",
  "params": { "threshold_value": 28, "comparison": ">",
              "duration_minutes": 10, "window_minutes": 15 },
  "severity": "warning",
  "enabled": true,
  "property_overrides": { "hotel_a": { "threshold_value": 26 } }
}
```

**Rules for generating valid configs**
1. `brick_class_target` MUST be one of the five Brick classes above (it must exist as a `BrickClass` node).
2. `condition_type` MUST be one of the four above; include exactly its params.
3. `severity` ∈ {`info`, `minor`, `warning`, `critical`}.
4. `property_overrides` keys are property ids (`hotel_a`, `hotel_b`, `hotel_c`); values override params for that site.
5. Durations/windows are minutes; `window_minutes` ≥ `duration_minutes`.

To add a brand-new detection algorithm (a new `condition_type`), implement a
`RuleEvaluator` in `services/afdd-engine/app/rules/` and register it with
`@register("<condition_type>")`, then add its key to `CONDITION_TYPES` in
`packages/shared/afdd_shared/rules.py`. Existing rules and APIs are unaffected.
