"""Tests for the ingestion + Brick-resolution logic using in-memory fakes.

These cover the pure transformation and the resolve->store flow without a live DB.
Full end-to-end (real Neo4j + TimescaleDB) lives in tests/integration (Phase 5).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from afdd_shared.models import Reading  # noqa: E402
from app import deps  # noqa: E402
from app.routers.ingest import _ingest, _to_resolved  # noqa: E402


CTX = {
    "hotel_a-r101-temperature": {
        "brick_class": "brick:Zone_Air_Temperature_Sensor",
        "location": "Room 101", "floor": 1, "property_id": "hotel_a",
        "datapoint": "temperature",
    },
    "hotel_b-r101-occupancy": {
        "brick_class": "brick:Occupancy_Sensor",
        "location": "Room 101", "floor": 1, "property_id": "hotel_b",
        "datapoint": "occupancy",
    },
}


class FakeNeo4j:
    async def resolve_devices_bulk(self, ids):
        return {i: CTX[i] for i in ids if i in CTX}


class FakeTimescale:
    def __init__(self):
        self.stored = []

    async def insert_readings(self, readings):
        self.stored.extend(readings)
        return len(readings)


def test_to_resolved_numeric():
    r = Reading(device_id="hotel_a-r101-temperature", datapoint="temperature",
                value=29.5, timestamp=1733500000)
    out = _to_resolved(r, CTX["hotel_a-r101-temperature"])
    assert out.value_num == 29.5
    assert out.value_text is None
    assert out.brick_class == "brick:Zone_Air_Temperature_Sensor"
    assert out.property_id == "hotel_a"


def test_to_resolved_occupancy_text_to_numeric():
    r = Reading(device_id="hotel_b-r101-occupancy", datapoint="occupancy",
                value="occupied", timestamp=1733500000)
    out = _to_resolved(r, CTX["hotel_b-r101-occupancy"])
    assert out.value_text == "occupied"
    assert out.value_num == 1.0


def test_ingest_accepts_known_rejects_unknown():
    deps.state.neo4j = FakeNeo4j()
    fake_ts = FakeTimescale()
    deps.state.timescale = fake_ts

    readings = [
        Reading(device_id="hotel_a-r101-temperature", datapoint="temperature",
                value=30.0, timestamp=1733500000),
        Reading(device_id="ghost-device", datapoint="temperature",
                value=22.0, timestamp=1733500000),
    ]
    result = asyncio.run(_ingest(readings))
    assert result.accepted == 1
    assert result.rejected == 1
    assert any("ghost-device" in e for e in result.errors)
    assert len(fake_ts.stored) == 1
    assert fake_ts.stored[0].brick_class == "brick:Zone_Air_Temperature_Sensor"


def test_ingest_brick_class_resolved_not_from_payload():
    # The payload never carries brick_class; it must come from the graph context.
    deps.state.neo4j = FakeNeo4j()
    deps.state.timescale = FakeTimescale()
    r = Reading(device_id="hotel_b-r101-occupancy", datapoint="occupancy",
                value="occupied", timestamp=1733500000)
    result = asyncio.run(_ingest([r]))
    assert result.accepted == 1
    assert deps.state.timescale.stored[0].brick_class == "brick:Occupancy_Sensor"
