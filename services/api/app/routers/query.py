"""Data query endpoints — latest reading and time-range data by device."""

from __future__ import annotations

from datetime import datetime, timezone

from afdd_shared.models import ReadingOut
from fastapi import APIRouter, HTTPException, Query

from ..deps import get_timescale

router = APIRouter(prefix="/api/v1", tags=["data-query"])


@router.get("/devices/{device_id}/latest", response_model=ReadingOut,
            summary="Latest reading for a device")
async def latest(device_id: str) -> ReadingOut:
    row = await get_timescale().latest(device_id)
    if not row:
        raise HTTPException(404, f"no readings for device {device_id}")
    return ReadingOut(**row)


@router.get("/devices/{device_id}/readings", response_model=list[ReadingOut],
            summary="Time-range readings for a device")
async def readings(
    device_id: str,
    from_ts: int = Query(..., alias="from", description="Unix epoch seconds (inclusive)"),
    to_ts: int = Query(..., alias="to", description="Unix epoch seconds (inclusive)"),
) -> list[ReadingOut]:
    start = datetime.fromtimestamp(from_ts, tz=timezone.utc)
    end = datetime.fromtimestamp(to_ts, tz=timezone.utc)
    rows = await get_timescale().range(device_id, start, end)
    return [ReadingOut(**r) for r in rows]
