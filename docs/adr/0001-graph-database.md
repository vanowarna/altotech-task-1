# ADR-0001 — Graph Database: Neo4j Community

**Status:** Accepted · **Date:** 2026-06-06

## Context
Buildings are inherently graphs: properties contain locations, locations contain devices, devices are typed by Brick classes and feed equipment. Brick Schema is itself an RDF graph ontology. The assessment requires modeling building semantics **natively as a graph**, where "find all AHUs on Floor 2" or "which sensors are in Room 101" are traversals, not multi-table joins. We must also pick a graph DB we can **defend** in the interview.

## Decision
Use **Neo4j Community Edition** as the topology + semantics store (the "Brick graph").

## Alternatives considered
- **Apache AGE (graph on PostgreSQL).** Attractive because graph + TimescaleDB could share one engine. Rejected for the POC: younger ecosystem, weaker tooling, openCypher gaps, and no first-class graph visualizer for the live demo. Revisit if operational simplicity (one DB) outweighs tooling.
- **RDF triplestore (GraphDB / RDFLib + SPARQL).** Truest fit for Brick (RDF-native, direct ontology import). Rejected: steepest learning curve, weakest time-series story, and hardest to defend live under time pressure. We instead model Brick semantics faithfully as labelled-property nodes/edges (see ADR-0002 and the Brick model doc).

## Consequences
- **+** Mature Cypher, excellent tooling and Neo4j Browser for demos; clean labelled-property model maps directly to Brick classes (node labels) and relationships (edges).
- **+** Constraints/indexes on `Device.id`, `Property.id` give O(1) device resolution at ingestion.
- **−** Not built for high-volume time-series writes → handled by ADR-0002 (TimescaleDB). This separation is a deliberate strength, not a workaround.
- **−** Community edition lacks clustering; acceptable for a POC.

## Scale path (100+ sites)
Neo4j read replicas / Aura for HA; partition queries by `property` to bound traversal cost; the Brick graph stays small (thousands of nodes) even at 400 properties because readings are *not* stored here.
