"""Pure sensor-value + anomaly generators (no I/O, fully unit-testable).

Produces realistic diurnal patterns per datapoint and injects the fault patterns
the AFDD engine is meant to catch: temperature spikes, stuck/flatline sensors,
schedule violations, and energy anomalies.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime


# --- Baseline (healthy) value models --------------------------------------

def _diurnal(hour: float, peak_hour: float = 15.0) -> float:
    """Normalized [-1, 1] daily cycle peaking at `peak_hour`."""
    return math.sin((hour - peak_hour + 6) / 24.0 * 2 * math.pi)


def is_occupied(dt: datetime, rng: random.Random) -> bool:
    """Probabilistic occupancy: high in evenings/nights, low midday."""
    h = dt.hour
    if 22 <= h or h < 7:
        p = 0.85          # guests in rooms overnight
    elif 7 <= h < 10:
        p = 0.5
    elif 18 <= h < 22:
        p = 0.7
    else:
        p = 0.2           # daytime, mostly out
    return rng.random() < p


def base_temperature(dt: datetime, occupied: bool, rng: random.Random) -> float:
    val = 23.0 + 1.8 * _diurnal(dt.hour + dt.minute / 60.0) + rng.gauss(0, 0.3)
    if occupied:
        val += 0.8
    return round(val, 2)


def base_humidity(dt: datetime, rng: random.Random) -> float:
    return round(55.0 + 4.0 * _diurnal(dt.hour, peak_hour=6) + rng.gauss(0, 1.0), 2)


def base_co2(dt: datetime, occupied: bool, rng: random.Random) -> float:
    val = 450.0 + (rng.uniform(350, 700) if occupied else rng.uniform(0, 60))
    return round(val + rng.gauss(0, 15), 1)


def base_power(dt: datetime, rng: random.Random) -> float:
    val = 5.0 + 2.5 * max(0.0, _diurnal(dt.hour + dt.minute / 60.0)) + rng.gauss(0, 0.25)
    return round(max(0.1, val), 2)


# --- Anomaly model --------------------------------------------------------

ANOMALY_TYPES = ("temperature_spike", "flatline", "schedule_violation", "energy_anomaly")


@dataclass
class Anomaly:
    """An active fault pattern bound to a device for a time range."""

    kind: str
    start_ts: int          # unix seconds (inclusive)
    end_ts: int            # unix seconds (exclusive); use a far-future value for "ongoing"
    frozen_value: float | None = None  # captured on first flatline tick

    def active_at(self, ts: int) -> bool:
        return self.start_ts <= ts < self.end_ts


def healthy_value(datapoint: str, dt: datetime, rng: random.Random) -> tuple[float | None, str | None]:
    """Return (numeric_value, text_value) for a healthy reading."""
    if datapoint == "temperature":
        return base_temperature(dt, is_occupied(dt, rng), rng), None
    if datapoint == "humidity":
        return base_humidity(dt, rng), None
    if datapoint == "co2":
        return base_co2(dt, is_occupied(dt, rng), rng), None
    if datapoint == "power":
        return base_power(dt, rng), None
    if datapoint == "occupancy":
        occ = is_occupied(dt, rng)
        return (1.0 if occ else 0.0), ("occupied" if occ else "unoccupied")
    raise ValueError(f"unknown datapoint {datapoint}")


def apply_anomaly(
    datapoint: str,
    dt: datetime,
    ts: int,
    base_num: float | None,
    base_text: str | None,
    anomaly: Anomaly,
    rng: random.Random,
) -> tuple[float | None, str | None]:
    """Mutate a healthy reading according to an active anomaly."""
    if anomaly.kind == "flatline":
        # Stuck sensor: zero variance. Freeze the first observed value.
        if anomaly.frozen_value is None:
            anomaly.frozen_value = base_num if base_num is not None else 0.0
        return anomaly.frozen_value, base_text

    if anomaly.kind == "temperature_spike" and datapoint == "temperature":
        return round(29.5 + rng.gauss(0, 0.4), 2), None  # sustained > 28C

    if anomaly.kind == "schedule_violation" and datapoint == "occupancy":
        return 1.0, "occupied"  # occupied regardless of hour (engine checks the clock)

    if anomaly.kind == "energy_anomaly" and datapoint == "power":
        spike = (base_num or 5.0) * rng.uniform(1.8, 2.4)  # well above 150% of average
        return round(spike, 2), None

    return base_num, base_text


def reading_value(
    datapoint: str,
    dt: datetime,
    ts: int,
    rng: random.Random,
    anomaly: Anomaly | None = None,
) -> tuple[float | str, dict]:
    """Top-level: produce the value to push, applying an anomaly if active.

    Returns (value, meta) where meta notes whether an anomaly was applied
    (useful for tests / observability).
    """
    base_num, base_text = healthy_value(datapoint, dt, rng)
    applied = None
    if anomaly is not None and anomaly.active_at(ts):
        base_num, base_text = apply_anomaly(datapoint, dt, ts, base_num, base_text, anomaly, rng)
        applied = anomaly.kind
    value: float | str = base_text if base_text is not None else (base_num if base_num is not None else 0.0)
    return value, {"anomaly": applied}
