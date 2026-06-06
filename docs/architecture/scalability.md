# Scalability & Extensibility Design

How the AFDD engine grows from 3 hotels to **100+ sites / 1000+ sensors**, how new
rule types are added **without code changes**, and how **cross-site patterns** are
detected.

## 1. Scaling the engine to 100+ sites

**Where the load is.** Three different resources, scaled independently:

| Bottleneck | POC | Scale path |
|---|---|---|
| Job distribution | one APScheduler process, all rules | shard evaluation by `property_id` across Celery/Temporal workers; each worker owns a slice of properties |
| Graph queries | single Neo4j, small graph | the Brick graph stays small (≈ nodes, not readings) even at 400 sites; add read replicas; scope every traversal by property to bound fan-out |
| Time-series | single TimescaleDB | hypertable chunking + compression + continuous aggregates; shard by property/time; cold chunks to object storage |

**Why the graph stays cheap.** Readings never enter Neo4j (ADR-0002). At 400
properties the graph is still on the order of 10⁵ nodes (properties, locations,
devices, rules, faults) — traversals like "devices of Brick class X in property Y"
remain millisecond-scale.

**Stateless engine.** All state lives in the datastores, so workers scale
horizontally with no coordination beyond the property-sharded job queue. Active-fault
dedup is enforced in the graph (a uniqueness-by-query check), not in process memory,
so two workers can never double-open the same fault.

**Evaluation sharding sketch**
```
scheduler (beat) ──emits──> "evaluate property=hotel_a rules=[...]" ──> worker pool
                              "evaluate property=hotel_b ..."             (N workers)
```
Each job: traverse targets for its property → window queries → fault writes. Linear
scale with worker count; no global lock.

## 2. New rule types without code changes

Two layers:
- **Rule instances are data.** A rule is a graph node (`brick_class_target`,
  `condition_type`, `params`, `property_overrides`). Operators create/edit rules via
  the API; no deploy needed. This already covers new thresholds, new target Brick
  classes, and per-property overrides.
- **Rule *types* use a plugin registry.** Each `condition_type` maps to a registered
  evaluator (`services/afdd-engine/app/rules/`, `@register("...")`). Adding a new
  detection algorithm = drop one evaluator file + register it; the orchestrator,
  fault manager, and APIs are untouched. The `params` dict is the typed contract
  between the rule node and its evaluator.

This is a lightweight rule DSL: `{condition_type + params}` is the language;
evaluators are its interpreters.

## 3. Cross-site pattern detection (aggregated graph analytics)

Because every fault is a node linked to a rule and a Brick class, cross-site questions
are graph aggregations:
- *"Which Brick class faults most across all hotels this week?"* — group faults by
  `raisedBy`→rule→Brick class.
- *"Do `CO2_Sensor` flatlines cluster on a vendor/floor?"* — traverse fault→device→
  location and group.
- *"Fleet-wide energy anomalies correlated with outdoor temperature?"* — join fault
  timestamps against the time-series aggregates.

These run as periodic analytics jobs over the (small) graph plus the continuous
aggregates, producing fleet KPIs without scanning raw readings. At larger scale they
become a separate read-replica/OLAP path so they never compete with the ingestion or
evaluation hot paths.

## 4. Multi-tenant isolation
Every node is reachable from exactly one `Property`; rules carry `property_overrides`.
Tenants share one platform and codebase but have isolated configs and per-property
thresholds — the exact "3 hotels with isolated configs" success metric, generalised
to 400.
