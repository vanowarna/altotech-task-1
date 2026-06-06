# Brick Schema Design

How the Brick ontology maps to the graph data model. Full detail:
[`docs/brick-schema/brick-model.md`](https://github.com/vanowarna/altotech-task-1/blob/main/docs/brick-schema/brick-model.md) ·
[external integration](https://github.com/vanowarna/altotech-task-1/blob/main/docs/brick-schema/external-integration.md).

## Mapping
Brick classes → node types; Brick relationships → edges.

```
(:Property)-[:hasPart]->(:Location)-[:hasPoint]->(:Device)
(:Device)-[:rdf_type]->(:BrickClass)      // native Brick typing
(:Device)-[:hasLocation]->(:Location)
(:Rule)-[:targets]->(:BrickClass)
(:Fault)-[:detectedOn]->(:Device)
(:Fault)-[:raisedBy]->(:Rule)
```

| Sensor type | Brick class |
|---|---|
| temperature | `brick:Zone_Air_Temperature_Sensor` |
| humidity | `brick:Zone_Air_Humidity_Sensor` |
| co2 | `brick:CO2_Sensor` |
| occupancy | `brick:Occupancy_Sensor` |
| power | `brick:Electrical_Power_Sensor` |

## Resolution at ingestion
Payload carries only `device_id, datapoint, value, timestamp`. The class is derived:
```cypher
MATCH (d:Device {id:$id})-[:rdf_type]->(b:BrickClass)
MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
RETURN b.uri AS brick_class, l.name AS location, p.id AS property_id
```

## Why this scales
A `Rule` targets a `BrickClass`; devices are typed by `rdf_type`. Add a device of an existing
class → instantly covered by matching rules. Add a class + rule → detection enabled fleet-wide
by traversal alone. No code changes — semantics are first-class graph data, not bolted-on tags.
