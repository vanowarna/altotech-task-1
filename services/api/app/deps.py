"""Shared application state + FastAPI dependencies (DB clients)."""

from __future__ import annotations

from afdd_shared.config import get_settings
from afdd_shared.neo4j_client import Neo4jClient
from afdd_shared.timescale import TimescaleClient


class AppState:
    """Holds long-lived DB clients, created on startup, closed on shutdown."""

    neo4j: Neo4jClient | None = None
    timescale: TimescaleClient | None = None


state = AppState()


def get_neo4j() -> Neo4jClient:
    assert state.neo4j is not None, "neo4j client not initialised"
    return state.neo4j


def get_timescale() -> TimescaleClient:
    assert state.timescale is not None, "timescale client not initialised"
    return state.timescale


async def startup() -> None:
    settings = get_settings()
    state.neo4j = Neo4jClient(settings)
    state.timescale = TimescaleClient(settings)
    await state.timescale.connect()


async def shutdown() -> None:
    if state.neo4j:
        await state.neo4j.close()
    if state.timescale:
        await state.timescale.close()
