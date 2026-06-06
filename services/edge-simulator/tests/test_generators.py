"""Unit tests for the simulator's value + anomaly generators."""

import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import generators as gen


def _dt(hour=12):
    return datetime(2025, 1, 1, hour, 0, tzinfo=timezone.utc)


def test_healthy_temperature_range():
    rng = random.Random(1)
    vals = [gen.base_temperature(_dt(h), False, rng) for h in range(24)]
    assert all(18 < v < 30 for v in vals)


def test_occupancy_state_values():
    rng = random.Random(2)
    num, text = gen.healthy_value("occupancy", _dt(23), rng)
    assert num in (0.0, 1.0)
    assert text in ("occupied", "unoccupied")


def test_temperature_spike_anomaly_exceeds_threshold():
    rng = random.Random(3)
    a = gen.Anomaly(kind="temperature_spike", start_ts=0, end_ts=10**12)
    ts = 1000
    # apply many times; spike must stay clearly above 28
    spikes = []
    for _ in range(20):
        v, meta = gen.reading_value("temperature", _dt(3), ts, rng, a)
        spikes.append(v)
        assert meta["anomaly"] == "temperature_spike"
    assert all(s > 28 for s in spikes)


def test_flatline_is_zero_variance():
    rng = random.Random(4)
    a = gen.Anomaly(kind="flatline", start_ts=0, end_ts=10**12)
    values = [gen.reading_value("co2", _dt(12), 500 + i, rng, a)[0] for i in range(15)]
    assert len(set(values)) == 1  # frozen -> zero variance


def test_energy_anomaly_above_150pct():
    rng = random.Random(5)
    a = gen.Anomaly(kind="energy_anomaly", start_ts=0, end_ts=10**12)
    base = gen.base_power(_dt(14), random.Random(5))
    v, meta = gen.reading_value("power", _dt(14), 10, rng, a)
    assert meta["anomaly"] == "energy_anomaly"
    assert v > 1.5 * 3.0  # comfortably above 150% of a typical baseline


def test_anomaly_inactive_outside_window():
    rng = random.Random(6)
    a = gen.Anomaly(kind="temperature_spike", start_ts=1000, end_ts=2000)
    v, meta = gen.reading_value("temperature", _dt(12), 500, rng, a)  # before window
    assert meta["anomaly"] is None
