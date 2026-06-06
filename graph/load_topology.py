"""Load the Brick graph into Neo4j from the declarative topology.

Steps:
  1. Apply schema.cypher (constraints + indexes).
  2. Create BrickClass nodes for every class in the Brick mapping.
  3. Create Property / Location / Device nodes and Brick-aligned relationships.

Idempotent: uses MERGE everywhere, safe to re-run. Run via:
    python graph/load_topology.py --topology deploy/topology.yaml
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

# Make the shared package importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "shared"))

from afdd_shared.brick import ALL_BRICK_CLASSES  # noqa: E402
from afdd_shared.topology import load_topology, topology_summary  # noqa: E402


def apply_schema(session, schema_path: Path) -> None:
    statements = [s.strip() for s in schema_path.read_text().split(";") if s.strip()]
    for stmt in statements:
        if stmt.startswith("//"):
            # strip leading comment-only lines
            lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("//")]
            stmt = "\n".join(lines).strip()
            if not stmt:
                continue
        session.run(stmt)
    print(f"  applied {len(statements)} schema statements")


def load_brick_classes(session) -> None:
    session.run(
        "UNWIND $uris AS uri MERGE (:BrickClass {uri: uri})",
        uris=ALL_BRICK_CLASSES,
    )
    print(f"  brick classes: {len(ALL_BRICK_CLASSES)}")


def load_properties(session, props) -> None:
    for p in props:
        session.run(
            """
            MERGE (prop:Property {id: $id})
            SET prop.name = $name, prop.timezone = $tz, prop.config = $config,
                prop.created_at = coalesce(prop.created_at, timestamp())
            """,
            id=p.id, name=p.name, tz=p.timezone, config=str(p.config),
        )
        for loc in p.locations:
            session.run(
                """
                MATCH (prop:Property {id: $pid})
                MERGE (l:Location {id: $id})
                SET l.name = $name, l.floor = $floor, l.type = $type
                MERGE (prop)-[:hasPart]->(l)
                """,
                pid=p.id, id=loc.id, name=loc.name, floor=loc.floor, type=loc.type,
            )
        for d in p.devices:
            session.run(
                """
                MATCH (l:Location {id: $loc_id})
                MERGE (d:Device:Point {id: $id})
                SET d.datapoint = $datapoint, d.brick_class = $brick_class,
                    d.unit = $unit, d.numeric = $numeric
                MERGE (l)-[:hasPoint]->(d)
                MERGE (d)-[:hasLocation]->(l)
                WITH d
                MATCH (b:BrickClass {uri: $brick_class})
                MERGE (d)-[:rdf_type]->(b)
                """,
                loc_id=d.location_id, id=d.id, datapoint=d.datapoint,
                brick_class=d.brick_class, unit=d.unit, numeric=d.numeric,
            )
        print(f"  loaded {p.id}: {len(p.locations)} locations, {len(p.devices)} devices")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", default="deploy/topology.yaml")
    parser.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "altotech123"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    schema_path = repo_root / "graph" / "schema.cypher"
    topo_path = (repo_root / args.topology) if not os.path.isabs(args.topology) else Path(args.topology)

    props = load_topology(str(topo_path))
    print("Topology summary:", topology_summary(props))

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    with driver.session() as session:
        print("Applying schema...")
        apply_schema(session, schema_path)
        print("Loading Brick classes...")
        load_brick_classes(session)
        print("Loading properties/locations/devices...")
        load_properties(session, props)
    driver.close()
    print("Graph load complete.")


if __name__ == "__main__":
    main()
