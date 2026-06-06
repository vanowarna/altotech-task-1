"""Dashboard data API — aggregates for the single-page UI."""

from __future__ import annotations

import json

from fastapi import APIRouter

from ..deps import get_neo4j

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

OPEN_STATUSES = ["detected", "active", "acknowledged"]


@router.get("/dashboard/summary", summary="Fault counts by property, severity distribution, recent")
async def summary() -> dict:
    neo4j = get_neo4j()

    by_property = await neo4j.run(
        """
        MATCH (p:Property)
        OPTIONAL MATCH (f:Fault)-[:detectedOn]->(:Device)-[:hasLocation]->(:Location)<-[:hasPart]-(p)
        WHERE f.status IN $open
        RETURN p.id AS property_id, p.name AS name, count(f) AS active_faults
        ORDER BY p.id
        """,
        open=OPEN_STATUSES,
    )

    by_severity = await neo4j.run(
        """
        MATCH (f:Fault) WHERE f.status IN $open
        RETURN f.severity AS severity, count(f) AS count
        ORDER BY count DESC
        """,
        open=OPEN_STATUSES,
    )

    by_status = await neo4j.run(
        "MATCH (f:Fault) RETURN f.status AS status, count(f) AS count ORDER BY status"
    )

    recent = await neo4j.run(
        """
        MATCH (f:Fault)-[:detectedOn]->(d:Device)
        MATCH (f)-[:raisedBy]->(r:Rule)
        MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
        RETURN f.id AS id, f.severity AS severity, f.status AS status,
               f.detected_at AS detected_at, f.context AS context,
               d.id AS device_id, p.id AS property_id, l.name AS location, r.name AS rule
        ORDER BY f.detected_at DESC LIMIT 10
        """
    )
    for r in recent:
        if r.get("context"):
            try:
                r["context"] = json.loads(r["context"])
            except (TypeError, ValueError):
                pass

    totals = {
        "active": sum(s["count"] for s in by_severity),
        "properties": len(by_property),
    }
    return {
        "totals": totals,
        "by_property": by_property,
        "by_severity": by_severity,
        "by_status": by_status,
        "recent_faults": recent,
    }
