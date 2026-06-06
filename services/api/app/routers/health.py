"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ..deps import get_neo4j, get_timescale

router = APIRouter(tags=["ops"])


@router.get("/health", summary="Liveness")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness (checks DB connectivity)")
async def ready() -> dict:
    checks = {"neo4j": False, "timescaledb": False}
    try:
        await get_neo4j().verify()
        checks["neo4j"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        await get_timescale().ping()
        checks["timescaledb"] = True
    except Exception:  # noqa: BLE001
        pass
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
