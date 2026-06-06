"""Rule evaluator base + registry.

Each evaluator is a pure function of its input (recent readings + params + now),
which makes the detection logic trivially unit-testable without any database.
New rule *types* register here; new rule *instances* are just graph data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class EvalInput:
    readings: list[dict]                 # recent window: [{time, value, value_text}, ...]
    params: dict                         # effective params (after property overrides)
    now: datetime
    baseline_avg: float | None = None    # optional precomputed baseline (energy rule)
    extra: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    faulted: bool
    detail: dict = field(default_factory=dict)


class RuleEvaluator(ABC):
    condition_type: str = ""

    @abstractmethod
    def evaluate(self, inp: EvalInput) -> EvalResult: ...


REGISTRY: dict[str, RuleEvaluator] = {}


def register(condition_type: str) -> Callable[[type[RuleEvaluator]], type[RuleEvaluator]]:
    def deco(cls: type[RuleEvaluator]) -> type[RuleEvaluator]:
        cls.condition_type = condition_type
        REGISTRY[condition_type] = cls()
        return cls
    return deco


def get_evaluator(condition_type: str) -> RuleEvaluator:
    if condition_type not in REGISTRY:
        raise KeyError(f"no evaluator registered for condition_type '{condition_type}'")
    return REGISTRY[condition_type]


# --- shared helpers -------------------------------------------------------

def numeric_values(readings: list[dict]) -> list[float]:
    return [float(r["value"]) for r in readings if r.get("value") is not None]


def within_last_minutes(readings: list[dict], now: datetime, minutes: float) -> list[dict]:
    cutoff = now.timestamp() - minutes * 60
    out = []
    for r in readings:
        t = r["time"]
        ts = t.timestamp() if isinstance(t, datetime) else float(t)
        if ts >= cutoff:
            out.append(r)
    return out
