"""Energy Anomaly rule — recent average exceeds a rolling baseline by pct_above.

The baseline average (over baseline_days, excluding the recent window) is computed
by the orchestrator and passed in as `baseline_avg`, so this evaluator stays pure.
"""

from __future__ import annotations

import statistics

from .base import EvalInput, EvalResult, RuleEvaluator, numeric_values, register, within_last_minutes


@register("energy_anomaly")
class EnergyAnomalyRule(RuleEvaluator):
    def evaluate(self, inp: EvalInput) -> EvalResult:
        pct_above = float(inp.params.get("pct_above", 150))
        window = float(inp.params.get("window_minutes", 15))

        recent = within_last_minutes(inp.readings, inp.now, window)
        values = numeric_values(recent)
        if not values or inp.baseline_avg is None or inp.baseline_avg <= 0:
            return EvalResult(False, {"reason": "no baseline or no recent data"})

        recent_avg = statistics.mean(values)
        ratio_pct = recent_avg / inp.baseline_avg * 100.0
        return EvalResult(
            ratio_pct > pct_above,
            {"recent_avg": round(recent_avg, 3), "baseline_avg": round(inp.baseline_avg, 3),
             "ratio_pct": round(ratio_pct, 1), "pct_above": pct_above},
        )
