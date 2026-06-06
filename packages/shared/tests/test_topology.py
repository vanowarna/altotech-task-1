"""Unit tests for the topology builder and Brick mapping."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from afdd_shared.brick import ALL_BRICK_CLASSES, brick_class_for, is_known_datapoint
from afdd_shared.topology import build_topology, topology_summary, all_devices


CONFIG = {
    "hotels": [
        {"id": "hotel_a", "name": "A", "floors": 2, "rooms": 10,
         "sensors": ["temperature", "humidity", "co2", "occupancy"], "power_meters_per_floor": 0},
        {"id": "hotel_b", "name": "B", "floors": 2, "rooms": 8,
         "sensors": ["temperature", "humidity", "co2", "occupancy"], "power_meters_per_floor": 1},
        {"id": "hotel_c", "name": "C", "floors": 3, "rooms": 12,
         "sensors": ["temperature", "humidity", "co2", "occupancy"], "power_meters_per_floor": 1},
    ]
}


def test_brick_mapping():
    assert brick_class_for("temperature") == "brick:Zone_Air_Temperature_Sensor"
    assert brick_class_for("power") == "brick:Electrical_Power_Sensor"
    assert is_known_datapoint("co2")
    assert not is_known_datapoint("nonsense")
    assert len(ALL_BRICK_CLASSES) == 5


def test_hotel_room_counts():
    props = build_topology(CONFIG)
    by_id = {p.id: p for p in props}
    # 10 + 8 + 12 = 30 rooms (guest_room locations)
    rooms = sum(1 for p in props for l in p.locations if l.type == "guest_room")
    assert rooms == 30
    # Hotel A: 10 rooms x 4 sensors = 40 devices, no power
    assert len(by_id["hotel_a"].devices) == 40


def test_power_meters_added():
    props = build_topology(CONFIG)
    by_id = {p.id: p for p in props}
    # Hotel B: 8 rooms x 4 = 32 + 2 floors x 1 power = 34
    power_devices = [d for d in by_id["hotel_b"].devices if d.datapoint == "power"]
    assert len(power_devices) == 2
    assert len(by_id["hotel_b"].devices) == 34


def test_device_ids_unique_and_typed():
    props = build_topology(CONFIG)
    devices = all_devices(props)
    ids = [d.id for d in devices]
    assert len(ids) == len(set(ids))  # unique
    for d in devices:
        assert d.brick_class == brick_class_for(d.datapoint)


def test_summary():
    props = build_topology(CONFIG)
    s = topology_summary(props)
    assert s["properties"] == 3
    # 40 + 34 + (48 + 3 power) = 40 + 34 + 51 = 125 devices
    assert s["devices"] == 125
