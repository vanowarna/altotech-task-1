"""Topology builder — turns a declarative hotel spec into the concrete graph.

Both the Neo4j loader and the edge simulator import this so device IDs and the
building structure are generated identically (DRY). Fully configurable: hotel
count, rooms, floors, sensor types, and power meters per floor.

Device ID convention:
    room sensor : "{hotel_id}-r{room_no}-{datapoint}"   e.g. hotel_a-r101-temperature
    power meter : "{hotel_id}-f{floor}-power{n}"         e.g. hotel_b-f1-power1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from .brick import BRICK_POINTS, brick_class_for


@dataclass(frozen=True)
class DeviceSpec:
    id: str
    datapoint: str
    brick_class: str
    unit: str
    numeric: bool
    location_id: str
    location_name: str
    floor: int
    property_id: str


@dataclass(frozen=True)
class LocationSpec:
    id: str
    name: str
    floor: int
    type: str
    property_id: str


@dataclass
class PropertySpec:
    id: str
    name: str
    timezone: str
    config: dict[str, Any] = field(default_factory=dict)
    locations: list[LocationSpec] = field(default_factory=list)
    devices: list[DeviceSpec] = field(default_factory=list)


def _room_number(floor: int, index_on_floor: int) -> int:
    """Floor 1 -> 101,102...; floor 2 -> 201,202..."""
    return floor * 100 + index_on_floor + 1


def build_property(spec: dict[str, Any]) -> PropertySpec:
    """Build one PropertySpec (locations + devices) from a hotel config dict."""
    hotel_id = spec["id"]
    floors = int(spec.get("floors", 1))
    rooms = int(spec["rooms"])
    sensors = list(spec.get("sensors", ["temperature", "humidity", "co2", "occupancy"]))
    power_per_floor = int(spec.get("power_meters_per_floor", 0))

    prop = PropertySpec(
        id=hotel_id,
        name=spec.get("name", hotel_id),
        timezone=spec.get("timezone", "UTC"),
        config=spec.get("config", {}),
    )

    # Distribute rooms across floors round-robin.
    per_floor_counts = [0] * floors
    for r in range(rooms):
        per_floor_counts[r % floors] += 1

    for floor in range(1, floors + 1):
        count = per_floor_counts[floor - 1]
        for i in range(count):
            room_no = _room_number(floor, i)
            loc_id = f"{hotel_id}-r{room_no}"
            loc = LocationSpec(
                id=loc_id,
                name=f"Room {room_no}",
                floor=floor,
                type="guest_room",
                property_id=hotel_id,
            )
            prop.locations.append(loc)
            for s in sensors:
                if s not in BRICK_POINTS:
                    raise ValueError(f"Unknown sensor type '{s}' in hotel '{hotel_id}'")
                bp = BRICK_POINTS[s]
                prop.devices.append(
                    DeviceSpec(
                        id=f"{loc_id}-{s}",
                        datapoint=s,
                        brick_class=bp.brick_class,
                        unit=bp.unit,
                        numeric=bp.numeric,
                        location_id=loc_id,
                        location_name=loc.name,
                        floor=floor,
                        property_id=hotel_id,
                    )
                )

        # Power meters live at the floor level (an electrical zone), not a room.
        if power_per_floor:
            floor_loc_id = f"{hotel_id}-f{floor}"
            prop.locations.append(
                LocationSpec(
                    id=floor_loc_id,
                    name=f"Floor {floor} electrical",
                    floor=floor,
                    type="electrical_zone",
                    property_id=hotel_id,
                )
            )
            for n in range(1, power_per_floor + 1):
                prop.devices.append(
                    DeviceSpec(
                        id=f"{floor_loc_id}-power{n}",
                        datapoint="power",
                        brick_class=brick_class_for("power"),
                        unit=BRICK_POINTS["power"].unit,
                        numeric=True,
                        location_id=floor_loc_id,
                        location_name=f"Floor {floor} electrical",
                        floor=floor,
                        property_id=hotel_id,
                    )
                )
    return prop


def build_topology(config: dict[str, Any]) -> list[PropertySpec]:
    """Build all properties from a parsed topology config dict."""
    return [build_property(h) for h in config["hotels"]]


def load_topology(path: str) -> list[PropertySpec]:
    """Load and build topology from a YAML file path."""
    with open(path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    return build_topology(config)


def all_devices(props: list[PropertySpec]) -> list[DeviceSpec]:
    return [d for p in props for d in p.devices]


def topology_summary(props: list[PropertySpec]) -> dict[str, Any]:
    return {
        "properties": len(props),
        "locations": sum(len(p.locations) for p in props),
        "devices": sum(len(p.devices) for p in props),
        "by_property": {
            p.id: {"locations": len(p.locations), "devices": len(p.devices)} for p in props
        },
    }
