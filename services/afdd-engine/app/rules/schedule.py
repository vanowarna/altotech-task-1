"""Schedule Violation rule — equipment/occupancy active outside operating hours.

Example: occupancy ON (or power above an on-threshold) after 22:00.
Time-of-day aware: it checks each in-window reading's own timestamp against the
operating hours, so it is correct regardless of when the engine runs.
"""

from __future__ import annotations

from datetime import datetime

from .base import EvalInput, EvalResult, RuleEvaluator, register, within_last_minutes


def _parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def _outside_hours(dt: datetime, start: str, end: str) -> bool:
    sh, sm = _parse_hhmm(start)
    eh, em = _parse_hhmm(end)
    minutes = dt.hour * 60 + dt.minute
    start_m = sh * 60 + sm
    end_m = eh * 60 + em
    if start_m <= end_m:
        return not (start_m <= minutes < end_m)
    # operating window wraps past midnight
    return not (minutes >= start_m or minutes < end_m)


@register("schedule_violation")
class ScheduleRule(RuleEvaluator):
    def evaluate(self, inp: EvalInput) -> EvalResult:
        window = float(inp.params.get("window_minutes", 15))
        start = inp.params.get("operating_start", "06:00")
        end = inp.params.get("operating_end", "22:00")
        on_value = float(inp.params.get("on_value", 1.0))

        recent = within_last_minutes(inp.readings, inp.now, window)
        violations = []
        for r in recent:
            t = r["time"]
            dt = t if isinstance(t, datetime) else datetime.fromtimestamp(float(t))
            active = False
            if r.get("value") is not None:
                active = float(r["value"]) >= on_value
            elif r.get("value_text"):
                active = str(r["value_text"]).lower() in ("occupied", "on", "online")
            if active and _outside_hours(dt, start, end):
                violations.append(dt.isoformat())

        return EvalResult(
            len(violations) > 0,
            {"operating_hours": f"{start}-{end}", "violations": violations[:5],
             "violation_count": len(violations)},
        )
