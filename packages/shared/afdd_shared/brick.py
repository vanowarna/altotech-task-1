"""Brick Schema class mapping — the single source of truth.

Maps a physical sensor datapoint to its Brick ontology class and unit. Reused by
the simulator (to know what to emit), the graph loader (to type Device nodes),
and the ingestion resolver (to validate). `brick_class` is therefore defined once
here and resolved from the graph at ingestion — never carried on the wire.

Reference: https://brickschema.org/
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrickPoint:
    """A Brick-typed measurement point definition."""

    datapoint: str          # logical sensor type, e.g. "temperature"
    brick_class: str        # Brick ontology class URI, e.g. "brick:Zone_Air_Temperature_Sensor"
    unit: str               # engineering unit, e.g. "degC"
    numeric: bool = True    # whether the value is numeric (vs. categorical state)


# Sensor type -> Brick class. Per assessment Section "Brick Class Mapping".
BRICK_POINTS: dict[str, BrickPoint] = {
    "temperature": BrickPoint("temperature", "brick:Zone_Air_Temperature_Sensor", "degC"),
    "humidity": BrickPoint("humidity", "brick:Zone_Air_Humidity_Sensor", "percent"),
    "co2": BrickPoint("co2", "brick:CO2_Sensor", "ppm"),
    "occupancy": BrickPoint("occupancy", "brick:Occupancy_Sensor", "state", numeric=False),
    "power": BrickPoint("power", "brick:Electrical_Power_Sensor", "kW"),
}

# Convenience reverse lookups.
BRICK_CLASS_BY_DATAPOINT: dict[str, str] = {k: v.brick_class for k, v in BRICK_POINTS.items()}
ALL_BRICK_CLASSES: list[str] = sorted({p.brick_class for p in BRICK_POINTS.values()})


def brick_class_for(datapoint: str) -> str:
    """Return the Brick class URI for a datapoint, or raise KeyError if unknown."""
    return BRICK_POINTS[datapoint].brick_class


def is_known_datapoint(datapoint: str) -> bool:
    return datapoint in BRICK_POINTS
