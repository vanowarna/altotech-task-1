"""Dashboard data API — aggregates for the single-page UI + 3D building heatmap."""

from __future__ import annotations

import json

from fastapi import APIRouter

from ..deps import get_neo4j, get_timescale

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
        ORDER BY f.detected_at DESC LIMIT 12
        """
    )
    for r in recent:
        if r.get("context"):
            try:
                r["context"] = json.loads(r["context"])
            except (TypeError, ValueError):
                pass

    totals = {"active": sum(s["count"] for s in by_severity), "properties": len(by_property)}
    return {
        "totals": totals,
        "by_property": by_property,
        "by_severity": by_severity,
        "by_status": by_status,
        "recent_faults": recent,
    }


@router.get("/dashboard/stats", summary="Live telemetry: device counts, ingest rate, health")
async def stats() -> dict:
    neo4j = get_neo4j()
    ts = get_timescale()

    counts = await neo4j.run(
        """
        RETURN
          count { (d:Device) } AS devices,
          count { (p:Property) } AS properties,
          count { (l:Location) } AS locations,
          count { (r:Rule) } AS rules
        """
    )
    faulted = await neo4j.run(
        """
        MATCH (f:Fault)-[:detectedOn]->(d:Device)
        WHERE f.status IN $open
        RETURN count(DISTINCT d) AS faulted_devices
        """,
        open=OPEN_STATUSES,
    )
    c = counts[0] if counts else {"devices": 0, "properties": 0, "locations": 0, "rules": 0}
    faulted_devices = faulted[0]["faulted_devices"] if faulted else 0

    readings_last_min = await ts.count_since(60)
    readings_last_5min = await ts.count_since(300)

    return {
        "devices": c["devices"],
        "properties": c["properties"],
        "locations": c["locations"],
        "rules": c["rules"],
        "faulted_devices": faulted_devices,
        "healthy_devices": max(0, c["devices"] - faulted_devices),
        "readings_last_min": readings_last_min,
        "ingest_per_sec": round(readings_last_min / 60.0, 1),
        "readings_last_5min": readings_last_5min,
    }


@router.get("/dashboard/topology", summary="Building structure + per-room fault status (for 3D)")
async def topology() -> dict:
    rows = await get_neo4j().run(
        """
        MATCH (p:Property)-[:hasPart]->(l:Location)
        OPTIONAL MATCH (l)-[:hasPoint]->(d:Device)
        OPTIONAL MATCH (f:Fault)-[:detectedOn]->(d)
          WHERE f.status IN $open
        WITH p, l, count(DISTINCT d) AS devices, count(DISTINCT f) AS active_faults,
             collect(DISTINCT f.severity) AS severities,
             collect(DISTINCT d{.id, .datapoint}) AS devicelist
        RETURN p.id AS property_id, p.name AS property_name,
               l.id AS location_id, l.name AS location_name, l.floor AS floor,
               l.type AS type, devices, active_faults, severities, devicelist
        ORDER BY p.id, l.floor, l.name
        """,
        open=OPEN_STATUSES,
    )

    sev_rank = {"critical": 4, "warning": 3, "minor": 2, "info": 1}
    props: dict[str, dict] = {}
    for r in rows:
        pid = r["property_id"]
        prop = props.setdefault(pid, {"id": pid, "name": r["property_name"], "rooms": []})
        worst = None
        for s in (r.get("severities") or []):
            if s and (worst is None or sev_rank.get(s, 0) > sev_rank.get(worst, 0)):
                worst = s
        prop["rooms"].append({
            "id": r["location_id"], "name": r["location_name"], "floor": r["floor"],
            "type": r["type"], "devices": r["devices"],
            "active_faults": r["active_faults"], "worst_severity": worst,
            "device_list": r.get("devicelist") or [],
        })
    return {"properties": list(props.values())}


@router.get("/dashboard/readings", summary="Latest reading per device (for the live 3D hover panel)")
async def readings_latest() -> dict:
    rows = await get_timescale().latest_all()
    out: dict[str, dict] = {}
    for r in rows:
        t = r.get("time")
        out[r["device_id"]] = {
            "datapoint": r["datapoint"],
            "value": r["value"],
            "value_text": r["value_text"],
            "time": int(t.timestamp()) if t else None,
        }
    return out
