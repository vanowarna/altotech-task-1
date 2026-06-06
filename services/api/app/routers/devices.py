"""Device & Property setup (minimal CRUD as graph nodes) + Brick-class queries."""

from __future__ import annotations

from afdd_shared.brick import brick_class_for, is_known_datapoint
from afdd_shared.models import DeviceIn, DeviceOut, PropertyIn
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_neo4j

router = APIRouter(prefix="/api/v1", tags=["setup"])


@router.post("/properties", summary="Create/Upsert a property (graph node)")
async def upsert_property(p: PropertyIn) -> dict:
    await get_neo4j().run(
        """
        MERGE (prop:Property {id: $id})
        SET prop.name = $name, prop.timezone = $tz, prop.config = $config,
            prop.created_at = coalesce(prop.created_at, timestamp())
        """,
        id=p.id, name=p.name, tz=p.timezone, config=str(p.config),
    )
    return {"status": "ok", "id": p.id}


@router.get("/properties", summary="List properties")
async def list_properties() -> list[dict]:
    return await get_neo4j().run(
        "MATCH (p:Property) RETURN p.id AS id, p.name AS name, p.timezone AS timezone ORDER BY p.id"
    )


@router.post("/devices", summary="Create/Upsert a device as a Brick-typed node")
async def upsert_device(d: DeviceIn) -> dict:
    if not is_known_datapoint(d.datapoint):
        raise HTTPException(400, f"unknown datapoint '{d.datapoint}'")
    brick_class = brick_class_for(d.datapoint)
    rows = await get_neo4j().run(
        """
        MATCH (l:Location {id: $loc_id})
        MERGE (d:Device:Point {id: $id})
        SET d.datapoint = $datapoint, d.brick_class = $brick_class
        MERGE (l)-[:hasPoint]->(d)
        MERGE (d)-[:hasLocation]->(l)
        WITH d
        MATCH (b:BrickClass {uri: $brick_class})
        MERGE (d)-[:rdf_type]->(b)
        RETURN d.id AS id
        """,
        loc_id=d.location_id, id=d.id, datapoint=d.datapoint, brick_class=brick_class,
    )
    if not rows:
        raise HTTPException(404, f"location '{d.location_id}' not found")
    return {"status": "ok", "id": d.id, "brick_class": brick_class}


@router.get("/devices", response_model=list[DeviceOut],
            summary="Query devices by Brick class via graph traversal")
async def query_devices(
    brick_class: str = Query(..., description="e.g. brick:Zone_Air_Temperature_Sensor"),
    property: str | None = Query(None, description="scope to a property id"),
    floor: int | None = Query(None, description="scope to a floor"),
) -> list[DeviceOut]:
    rows = await get_neo4j().devices_by_brick_class(brick_class, property, floor)
    return [DeviceOut(**r) for r in rows]
