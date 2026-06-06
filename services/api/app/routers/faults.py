"""Fault management API — query, inspect, acknowledge, resolve, and annotate faults."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from afdd_shared.models import FaultOut, NoteIn
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_neo4j

router = APIRouter(prefix="/api/v1", tags=["faults"])

OPEN_STATUSES = ["detected", "active", "acknowledged"]


def _row_to_fault(r: dict) -> FaultOut:
    ctx = r.get("context")
    return FaultOut(
        id=r["id"], severity=r["severity"], status=r["status"],
        detected_at=r.get("detected_at"), resolved_at=r.get("resolved_at"),
        device_id=r.get("device_id"), property_id=r.get("property_id"),
        location=r.get("location"), rule=r.get("rule"), brick_class=r.get("brick_class"),
        context=json.loads(ctx) if ctx else None,
        notes=r.get("notes") or [],
    )


@router.get("/faults", response_model=list[FaultOut], summary="List/filter faults")
async def list_faults(
    property: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None, description="active|acknowledged|resolved|detected"),
    limit: int = Query(100, le=1000),
) -> list[FaultOut]:
    rows = await get_neo4j().run(
        """
        MATCH (f:Fault)-[:detectedOn]->(d:Device)
        MATCH (f)-[:raisedBy]->(r:Rule)
        MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
        WHERE ($property IS NULL OR p.id = $property)
          AND ($severity IS NULL OR f.severity = $severity)
          AND ($status IS NULL OR f.status = $status)
        RETURN f.id AS id, f.severity AS severity, f.status AS status,
               f.detected_at AS detected_at, f.resolved_at AS resolved_at,
               f.context AS context, f.notes AS notes,
               d.id AS device_id, p.id AS property_id, l.name AS location,
               r.name AS rule, r.brick_class_target AS brick_class
        ORDER BY f.detected_at DESC
        LIMIT $limit
        """,
        property=property, severity=severity, status=status, limit=limit,
    )
    return [_row_to_fault(r) for r in rows]


@router.get("/faults/{fault_id}", response_model=FaultOut, summary="Fault details + context")
async def get_fault(fault_id: str) -> FaultOut:
    rows = await get_neo4j().run(
        """
        MATCH (f:Fault {id: $id})-[:detectedOn]->(d:Device)
        MATCH (f)-[:raisedBy]->(r:Rule)
        MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
        RETURN f.id AS id, f.severity AS severity, f.status AS status,
               f.detected_at AS detected_at, f.resolved_at AS resolved_at,
               f.context AS context, f.notes AS notes,
               d.id AS device_id, p.id AS property_id, l.name AS location,
               r.name AS rule, r.brick_class_target AS brick_class
        """,
        id=fault_id,
    )
    if not rows:
        raise HTTPException(404, "fault not found")
    return _row_to_fault(rows[0])


async def _set_status(fault_id: str, status: str, resolved: bool = False) -> FaultOut:
    ts = int(datetime.now(timezone.utc).timestamp())
    rows = await get_neo4j().run(
        """
        MATCH (f:Fault {id: $id})
        SET f.status = $status""" + (", f.resolved_at = $ts" if resolved else "") + """
        RETURN f.id AS id
        """,
        id=fault_id, status=status, ts=ts,
    )
    if not rows:
        raise HTTPException(404, "fault not found")
    return await get_fault(fault_id)


@router.post("/faults/{fault_id}/ack", response_model=FaultOut, summary="Acknowledge a fault")
async def ack_fault(fault_id: str) -> FaultOut:
    return await _set_status(fault_id, "acknowledged")


@router.post("/faults/{fault_id}/resolve", response_model=FaultOut, summary="Resolve a fault")
async def resolve_fault(fault_id: str) -> FaultOut:
    return await _set_status(fault_id, "resolved", resolved=True)


@router.post("/faults/{fault_id}/notes", response_model=FaultOut, summary="Add a note to a fault")
async def add_note(fault_id: str, body: NoteIn) -> FaultOut:
    rows = await get_neo4j().run(
        """
        MATCH (f:Fault {id: $id})
        SET f.notes = coalesce(f.notes, []) + $note
        RETURN f.id AS id
        """,
        id=fault_id, note=body.note,
    )
    if not rows:
        raise HTTPException(404, "fault not found")
    return await get_fault(fault_id)
