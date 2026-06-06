"""Seed the default rule set into the graph (idempotent). Runs on engine startup."""

from __future__ import annotations

import json
import logging

from afdd_shared.neo4j_client import Neo4jClient
from afdd_shared.rules import DEFAULT_RULES

log = logging.getLogger("afdd.seed")


async def seed_default_rules(neo4j: Neo4jClient) -> int:
    count = 0
    for rule in DEFAULT_RULES:
        await neo4j.run(
            """
            MERGE (r:Rule {id: $id})
            SET r.name = $name, r.condition_type = $condition_type,
                r.params = $params, r.severity = $severity, r.enabled = $enabled,
                r.property_overrides = $property_overrides,
                r.brick_class_target = $brick_class_target
            WITH r
            MATCH (b:BrickClass {uri: $brick_class_target})
            MERGE (r)-[:targets]->(b)
            """,
            id=rule["id"], name=rule["name"], condition_type=rule["condition_type"],
            params=json.dumps(rule["params"]), severity=rule["severity"],
            enabled=rule["enabled"], property_overrides=json.dumps(rule["property_overrides"]),
            brick_class_target=rule["brick_class_target"],
        )
        count += 1
    log.info("seeded default rules", extra={"count": count})
    return count
