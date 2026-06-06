"""FastAPI application entrypoint for the AFDD platform API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from afdd_shared.logging_setup import setup_logging
from fastapi import FastAPI

from . import deps
from .routers import devices, health, ingest, query

setup_logging(os.environ.get("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await deps.startup()
    yield
    await deps.shutdown()


app = FastAPI(
    title="AltoTech Multi-Site AFDD API",
    description=(
        "Brick-aware ingestion, data query, and (Phase 3) rule/fault management for the "
        "Multi-Site AFDD platform. Topology + Brick semantics live in Neo4j; high-volume "
        "readings live in TimescaleDB."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(devices.router)

# Prometheus metrics at /metrics (bonus; optional dependency).
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except Exception:  # noqa: BLE001
    pass


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "afdd-api", "docs": "/docs", "health": "/health"}
