"""Async TimescaleDB (Postgres) client — the high-volume readings store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

from .config import Settings
from .models import ResolvedReading


class TimescaleClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._settings.ts_dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def ping(self) -> bool:
        assert self._pool
        async with self._pool.acquire() as con:
            await con.execute("SELECT 1")
        return True

    async def insert_readings(self, readings: list[ResolvedReading]) -> int:
        assert self._pool
        rows = [
            (
                datetime.fromtimestamp(r.timestamp, tz=timezone.utc),
                r.device_id,
                r.property_id,
                r.brick_class,
                r.datapoint,
                r.value_num,
                r.value_text,
            )
            for r in readings
        ]
        async with self._pool.acquire() as con:
            await con.executemany(
                """
                INSERT INTO readings
                    (time, device_id, property_id, brick_class, datapoint, value, value_text)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                """,
                rows,
            )
        return len(rows)

    async def latest(self, device_id: str) -> Optional[dict[str, Any]]:
        assert self._pool
        async with self._pool.acquire() as con:
            row = await con.fetchrow(
                """
                SELECT time, device_id, datapoint, value, value_text, brick_class
                FROM readings WHERE device_id = $1 ORDER BY time DESC LIMIT 1
                """,
                device_id,
            )
        return dict(row) if row else None

    async def range(
        self, device_id: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        assert self._pool
        async with self._pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT time, device_id, datapoint, value, value_text, brick_class
                FROM readings
                WHERE device_id = $1 AND time >= $2 AND time <= $3
                ORDER BY time ASC
                """,
                device_id,
                start,
                end,
            )
        return [dict(r) for r in rows]

    async def window(self, device_id: str, minutes: int) -> list[dict[str, Any]]:
        """Recent window used by the AFDD evaluator."""
        assert self._pool
        async with self._pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT time, value, value_text FROM readings
                WHERE device_id = $1 AND time >= now() - ($2 || ' minutes')::interval
                ORDER BY time ASC
                """,
                device_id,
                str(minutes),
            )
        return [dict(r) for r in rows]
