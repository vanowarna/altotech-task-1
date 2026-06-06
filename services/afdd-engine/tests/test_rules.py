"""Unit tests for the four AFDD rule evaluators (pure logic, no DB)."""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rules import REGISTRY, EvalInput, get_evaluator  # noqa: E402


NOW = datetime(2025, 1, 1, 23, 30, tzinfo=timezone.utc)  # after-hours for schedule test


def _series(values, start_min_ago, step_min=1):
    """Build readings ending ~now, oldest first."""
    out = []
    n = len(values)
    for i, v in enumerate(values):
        t = NOW - timedelta(minutes=start_min_ago - i * step_min)
        out.append({"time": t, "value": v, "value_text": None})
    return out


def test_registry_has_all_four():
    assert set(REGISTRY) == {"threshold_exceeded", "flatline", "schedule_violation", "energy_anomaly"}


def test_threshold_faults_when_sustained():
    ev = get_evaluator("threshold_exceeded")
    readings = _series([29.0, 29.5, 30.0, 29.8, 30.1], start_min_ago=8)
    res = ev.evaluate(EvalInput(readings, {"threshold_value": 28, "comparison": ">",
                                           "duration_minutes": 10, "window_minutes": 15}, NOW))
    assert res.faulted


def test_threshold_ok_when_within_limit():
    ev = get_evaluator("threshold_exceeded")
    readings = _series([24.0, 24.5, 23.8, 25.0], start_min_ago=8)
    res = ev.evaluate(EvalInput(readings, {"threshold_value": 28, "comparison": ">",
                                           "duration_minutes": 10, "window_minutes": 15}, NOW))
    assert not res.faulted


def test_flatline_detects_zero_variance():
    ev = get_evaluator("flatline")
    readings = _series([500.0] * 10, start_min_ago=25)
    res = ev.evaluate(EvalInput(readings, {"window_minutes": 30, "min_stddev": 0.01,
                                           "min_samples": 5}, NOW))
    assert res.faulted
    assert res.detail["stddev"] == 0.0


def test_flatline_ok_when_varying():
    ev = get_evaluator("flatline")
    readings = _series([450, 470, 460, 480, 455, 465], start_min_ago=25)
    res = ev.evaluate(EvalInput(readings, {"window_minutes": 30, "min_stddev": 0.01,
                                           "min_samples": 5}, NOW))
    assert not res.faulted


def test_schedule_violation_after_hours():
    ev = get_evaluator("schedule_violation")
    # occupancy = occupied at 23:30 -> outside 06:00-22:00
    readings = [{"time": NOW, "value": 1.0, "value_text": "occupied"}]
    res = ev.evaluate(EvalInput(readings, {"operating_start": "06:00", "operating_end": "22:00",
                                           "window_minutes": 15, "on_value": 1.0}, NOW))
    assert res.faulted


def test_schedule_ok_during_hours():
    ev = get_evaluator("schedule_violation")
    midday = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    readings = [{"time": midday, "value": 1.0, "value_text": "occupied"}]
    res = ev.evaluate(EvalInput(readings, {"operating_start": "06:00", "operating_end": "22:00",
                                           "window_minutes": 15, "on_value": 1.0}, midday))
    assert not res.faulted


def test_energy_anomaly_above_threshold():
    ev = get_evaluator("energy_anomaly")
    readings = _series([11.0, 12.0, 11.5], start_min_ago=10)
    res = ev.evaluate(EvalInput(readings, {"pct_above": 150, "window_minutes": 15},
                                NOW, baseline_avg=5.0))
    assert res.faulted
    assert res.detail["ratio_pct"] > 150


def test_energy_anomaly_normal():
    ev = get_evaluator("energy_anomaly")
    readings = _series([5.2, 5.0, 5.4], start_min_ago=10)
    res = ev.evaluate(EvalInput(readings, {"pct_above": 150, "window_minutes": 15},
                                NOW, baseline_avg=5.0))
    assert not res.faulted
