"""Rule vocabulary + default rule set — shared by the engine and the API.

Condition types are the plugin seam: adding a new rule *type* means registering a
new evaluator in the engine (see services/afdd-engine/app/rules/) and adding its key
here. Rule *instances* are data (graph nodes) and need no code change.
"""

from __future__ import annotations

# Supported condition types and the params each expects.
CONDITION_TYPES: dict[str, dict] = {
    "threshold_exceeded": {
        "params": ["threshold_value", "comparison", "duration_minutes", "window_minutes"],
        "doc": "value comparison vs threshold sustained over duration_minutes",
    },
    "flatline": {
        "params": ["window_minutes", "min_stddev", "min_samples"],
        "doc": "near-zero variance (stuck sensor) over window_minutes",
    },
    "schedule_violation": {
        "params": ["operating_start", "operating_end", "window_minutes", "on_value"],
        "doc": "device active outside operating hours",
    },
    "energy_anomaly": {
        "params": ["pct_above", "baseline_days", "window_minutes"],
        "doc": "recent average exceeds rolling baseline average by pct_above",
    },
}


def is_valid_condition_type(ct: str) -> bool:
    return ct in CONDITION_TYPES


# Default rules seeded into the graph on engine startup (idempotent).
# property_overrides override params for a specific property id.
DEFAULT_RULES: list[dict] = [
    {
        "id": "rule_high_temperature",
        "name": "High Temperature Alert",
        "brick_class_target": "brick:Zone_Air_Temperature_Sensor",
        "condition_type": "threshold_exceeded",
        "params": {
            "threshold_value": 28.0,
            "comparison": ">",
            "duration_minutes": 10,
            "window_minutes": 15,
        },
        "severity": "warning",
        "enabled": True,
        "property_overrides": {"hotel_a": {"threshold_value": 26.0}},
    },
    {
        "id": "rule_sensor_flatline_co2",
        "name": "CO2 Sensor Flatline",
        "brick_class_target": "brick:CO2_Sensor",
        "condition_type": "flatline",
        "params": {"window_minutes": 30, "min_stddev": 0.01, "min_samples": 5},
        "severity": "minor",
        "enabled": True,
        "property_overrides": {},
    },
    {
        "id": "rule_schedule_violation",
        "name": "After-Hours Occupancy",
        "brick_class_target": "brick:Occupancy_Sensor",
        "condition_type": "schedule_violation",
        "params": {
            "operating_start": "06:00",
            "operating_end": "22:00",
            "window_minutes": 15,
            "on_value": 1.0,
        },
        "severity": "info",
        "enabled": True,
        "property_overrides": {},
    },
    {
        "id": "rule_energy_anomaly",
        "name": "Energy Consumption Anomaly",
        "brick_class_target": "brick:Electrical_Power_Sensor",
        "condition_type": "energy_anomaly",
        "params": {"pct_above": 150.0, "baseline_days": 7, "window_minutes": 15},
        "severity": "warning",
        "enabled": True,
        "property_overrides": {},
    },
]
