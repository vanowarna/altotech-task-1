"""Temperature Excursion / threshold rule.

Fault if values breach the threshold for a sustained duration within the window.
Example: value > 28 for >= 10 consecutive minutes.
"""

from __future__ import annotations

from .base import EvalInput, EvalResult, RuleEvaluator, numeric_values, register, within_last_minutes


@register("threshold_exceeded")
class ThresholdRule(RuleEvaluator):
    def evaluate(self, inp: EvalInput) -> EvalResult:
        threshold = float(inp.params["threshold_value"])
        comparison = inp.params.get("comparison", ">")
        duration = float(inp.params.get("duration_minutes", 10))

        recent = within_last_minutes(inp.readings, inp.now, duration)
        values = numeric_values(recent)
        if len(values) < 2:
            return EvalResult(False, {"reason": "insufficient samples in duration window"})

        def breaches(v: float) -> bool:
            return v > threshold if comparison == ">" else v < threshold

        sustained = all(breaches(v) for v in values)
        return EvalResult(
            sustained,
            {
                "threshold": threshold,
                "comparison": comparison,
                "duration_minutes": duration,
                "samples": values[-5:],
                "min": min(values),
                "max": max(values),
            },
        )
