"""Sensor Flatline rule — detects a stuck sensor (near-zero variance)."""

from __future__ import annotations

import statistics

from .base import EvalInput, EvalResult, RuleEvaluator, numeric_values, register, within_last_minutes


@register("flatline")
class FlatlineRule(RuleEvaluator):
    def evaluate(self, inp: EvalInput) -> EvalResult:
        window = float(inp.params.get("window_minutes", 30))
        min_stddev = float(inp.params.get("min_stddev", 0.01))
        min_samples = int(inp.params.get("min_samples", 5))

        recent = within_last_minutes(inp.readings, inp.now, window)
        values = numeric_values(recent)
        if len(values) < min_samples:
            return EvalResult(False, {"reason": "insufficient samples", "samples": len(values)})

        stddev = statistics.pstdev(values)
        return EvalResult(
            stddev <= min_stddev,
            {"stddev": round(stddev, 6), "min_stddev": min_stddev,
             "samples": len(values), "value": values[-1]},
        )
