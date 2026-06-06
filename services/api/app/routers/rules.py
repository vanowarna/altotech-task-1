"""Rule management API — CRUD over Rule nodes + enable/disable per property.

Rules are configuration stored as graph nodes. params and property_overrides are
persisted as JSON strings (Neo4j properties are primitive) and parsed on read.
"""

from __future__ import annotations

import json
import uuid

from afdd_shared.models import RuleIn, RuleOut
from afdd_shared.rules import is_valid_condition_type
from fastapi import APIRouter, Body, HTTPException, Query

from ..deps import get_neo4j

router = APIRouter(prefix="/api/v1", tags=["rules"])


def _row_to_rule(r: dict) -> RuleOut:
    return RuleOut(
        id=r["id"], name=r["name"], brick_class_target=r["brick_class_target"],
        condition_type=r["condition_type"], severity=r["severity"], enabled=r["enabled"],
        params=json.loads(r.get("params") or "{}"),
        property_overrides=json.loads(r.get("property_overrides") or "{}"),
    )


async def _upsert(rule: RuleIn) -> RuleOut:
    if not is_valid_condition_type(rule.condition_type):
        raise HTTPException(400, f"unknown condition_type '{rule.condition_type}'")
    rid = rule.id or f"rule_{uuid.uuid4().hex[:10]}"
    rows = await get_neo4j().run(
        """
        MATCH (b:BrickClass {uri: $brick})
        MERGE (r:Rule {id: $id})
        SET r.name = $name, r.condition_type = $ct, r.params = $params,
            r.severity = $sev, r.enabled = $enabled,
            r.property_overrides = $po, r.brick_class_target = $brick
        MERGE (r)-[:targets]->(b)
        RETURN r.id AS id, r.name AS name, r.brick_class_target AS brick_class_target,
               r.condition_type AS condition_type, r.params AS params, r.severity AS severity,
               r.enabled AS enabled, r.property_overrides AS property_overrides
        """,
        id=rid, name=rule.name, ct=rule.condition_type, params=json.dumps(rule.params),
        sev=rule.severity, enabled=rule.enabled, po=json.dumps(rule.property_overrides),
        brick=rule.brick_class_target,
    )
    if not rows:
        raise HTTPException(404, f"brick class '{rule.brick_class_target}' not found")
    return _row_to_rule(rows[0])


@router.post("/rules", response_model=RuleOut, summary="Create a rule")
async def create_rule(rule: RuleIn) -> RuleOut:
    return await _upsert(rule)


@router.get("/rules", response_model=list[RuleOut], summary="List rules")
async def list_rules() -> list[RuleOut]:
    rows = await get_neo4j().run(
        """
        MATCH (r:Rule)
        RETURN r.id AS id, r.name AS name, r.brick_class_target AS brick_class_target,
               r.condition_type AS condition_type, r.params AS params, r.severity AS severity,
               r.enabled AS enabled, r.property_overrides AS property_overrides
        ORDER BY r.id
        """
    )
    return [_row_to_rule(r) for r in rows]


@router.get("/rules/{rule_id}", response_model=RuleOut, summary="Get a rule")
async def get_rule(rule_id: str) -> RuleOut:
    rows = await get_neo4j().run(
        """
        MATCH (r:Rule {id: $id})
        RETURN r.id AS id, r.name AS name, r.brick_class_target AS brick_class_target,
               r.condition_type AS condition_type, r.params AS params, r.severity AS severity,
               r.enabled AS enabled, r.property_overrides AS property_overrides
        """,
        id=rule_id,
    )
    if not rows:
        raise HTTPException(404, "rule not found")
    return _row_to_rule(rows[0])


@router.put("/rules/{rule_id}", response_model=RuleOut, summary="Update a rule")
async def update_rule(rule_id: str, rule: RuleIn) -> RuleOut:
    rule.id = rule_id
    return await _upsert(rule)


@router.delete("/rules/{rule_id}", summary="Delete a rule")
async def delete_rule(rule_id: str) -> dict:
    await get_neo4j().run("MATCH (r:Rule {id: $id}) DETACH DELETE r", id=rule_id)
    return {"status": "deleted", "id": rule_id}


@router.patch("/rules/{rule_id}/enable", response_model=RuleOut,
              summary="Enable/disable a rule globally or per property")
async def enable_rule(
    rule_id: str,
    enabled: bool = Query(...),
    property: str | None = Query(None, description="scope the toggle to one property"),
) -> RuleOut:
    neo4j = get_neo4j()
    if property is None:
        await neo4j.run("MATCH (r:Rule {id:$id}) SET r.enabled=$en", id=rule_id, en=enabled)
    else:
        # Per-property toggle via property_overrides.{property}.enabled
        rows = await neo4j.run("MATCH (r:Rule {id:$id}) RETURN r.property_overrides AS po", id=rule_id)
        if not rows:
            raise HTTPException(404, "rule not found")
        po = json.loads(rows[0].get("po") or "{}")
        po.setdefault(property, {})["enabled"] = enabled
        await neo4j.run("MATCH (r:Rule {id:$id}) SET r.property_overrides=$po",
                        id=rule_id, po=json.dumps(po))
    return await get_rule(rule_id)
