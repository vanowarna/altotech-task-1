"""Ingestion endpoints — receive readings, resolve Brick context via the graph,
persist to TimescaleDB. `brick_class` is resolved here, never carried on the wire.
"""

from __future__ import annotations

import logging

from afdd_shared.models import BatchReadings, IngestResult, Reading, ResolvedReading
from fastapi import APIRouter, Depends

from ..deps import get_neo4j, get_timescale

log = logging.getLogger("api.ingest")
router = APIRouter(prefix="/api/v1", tags=["ingestion"])


def _to_resolved(reading: Reading, ctx: dict) -> ResolvedReading:
    value_num: float | None
    value_text: str | None
    if isinstance(reading.value, str):
        # Categorical (e.g. occupancy state); also encode a numeric flag when possible.
        value_text = reading.value
        value_num = {"occupied": 1.0, "unoccupied": 0.0, "online": 1.0, "offline": 0.0}.get(
            reading.value.lower()
        )
    else:
        value_num = float(reading.value)
        value_text = None
    return ResolvedReading(
        device_id=reading.device_id,
        datapoint=reading.datapoint,
        value_num=value_num,
        value_text=value_text,
        timestamp=reading.timestamp,
        brick_class=ctx["brick_class"],
        property_id=ctx["property_id"],
        location=ctx["location"],
    )


async def _ingest(readings: list[Reading]) -> IngestResult:
    neo4j = get_neo4j()
    ts = get_timescale()

    ids = list({r.device_id for r in readings})
    resolved_ctx = await neo4j.resolve_devices_bulk(ids)

    to_store: list[ResolvedReading] = []
    errors: list[str] = []
    for r in readings:
        ctx = resolved_ctx.get(r.device_id)
        if ctx is None:
            errors.append(f"unknown device: {r.device_id}")
            continue
        try:
            to_store.append(_to_resolved(r, ctx))
        except (ValueError, TypeError) as exc:
            errors.append(f"bad value for {r.device_id}: {exc}")

    if to_store:
        await ts.insert_readings(to_store)

    result = IngestResult(accepted=len(to_store), rejected=len(errors), errors=errors[:20])
    log.info("ingest", extra={"accepted": result.accepted, "rejected": result.rejected})
    return result


@router.post("/ingest", response_model=IngestResult, summary="Ingest a single reading")
async def ingest_single(reading: Reading) -> IngestResult:
    return await _ingest([reading])


@router.post("/ingest/batch", response_model=IngestResult, summary="Ingest a batch of readings")
async def ingest_batch(batch: BatchReadings) -> IngestResult:
    return await _ingest(batch.readings)
