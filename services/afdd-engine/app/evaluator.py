"""Condition Evaluator / orchestrator — one pass over all enabled rules.

For each rule:
  1. Resolve target devices by Brick class (graph traversal), scoped per property.
  2. Pull the recent time-series window (and a baseline for energy rules).
  3. Apply the registered evaluator with property-overridden params.
  4. Open or resolve faults (dedup in the FaultManager) and dispatch alerts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from afdd_shared.neo4j_client import Neo4jClient
from afdd_shared.timescale import TimescaleClient

from .dispatcher import AlertDispatcher
from .fault_manager import FaultManager
from .rules import EvalInput, get_evaluator

log = logging.getLogger("afdd.evaluator")


def _merge_params(base: dict, overrides: dict, property_id: str) -> dict:
    eff = dict(base)
    po = overrides.get(property_id) if overrides else None
    if isinstance(po, dict):
        eff.update(po)
    return eff


class AfddEvaluator:
    def __init__(self, neo4j: Neo4jClient, ts: TimescaleClient, dispatcher: AlertDispatcher):
        self.neo4j = neo4j
        self.ts = ts
        self.faults = FaultManager(neo4j)
        self.dispatcher = dispatcher

    async def load_rules(self) -> list[dict]:
        rows = await self.neo4j.run(
            """
            MATCH (r:Rule)-[:targets]->(b:BrickClass)
            WHERE r.enabled = true
            RETURN r.id AS id, r.name AS name, b.uri AS brick_class_target,
                   r.condition_type AS condition_type, r.params AS params,
                   r.severity AS severity, r.property_overrides AS property_overrides
            """
        )
        for r in rows:
            r["params"] = json.loads(r.get("params") or "{}")
            r["property_overrides"] = json.loads(r.get("property_overrides") or "{}")
        return rows

    async def evaluate_all(self) -> dict:
        now = datetime.now(timezone.utc)
        rules = await self.load_rules()
        opened = resolved = checked = 0

        for rule in rules:
            try:
                evaluator = get_evaluator(rule["condition_type"])
            except KeyError:
                log.warning("unknown condition_type", extra={"rule": rule["id"]})
                continue

            targets = await self.neo4j.devices_by_brick_class(rule["brick_class_target"])
            for dev in targets:
                checked += 1
                # Isolate each device: one bad evaluation must never abort the cycle.
                try:
                    params = _merge_params(rule["params"], rule["property_overrides"], dev["property_id"])
                    window = int(params.get("window_minutes", 15))
                    readings = await self.ts.window(dev["id"], window)

                    baseline = None
                    if rule["condition_type"] == "energy_anomaly":
                        baseline = await self.ts.baseline_avg(
                            dev["id"], int(params.get("baseline_days", 7)), window
                        )

                    result = evaluator.evaluate(
                        EvalInput(readings=readings, params=params, now=now, baseline_avg=baseline)
                    )

                    if result.faulted:
                        context = {
                            "rule": rule["name"], "brick_class": rule["brick_class_target"],
                            "location": dev.get("location"), "window_minutes": window,
                            "detail": result.detail,
                        }
                        fault_id = await self.faults.open_fault(
                            dev["id"], rule["id"], rule["severity"], context
                        )
                        if fault_id:
                            opened += 1
                            await self.dispatcher.dispatch({
                                "event": "fault.detected", "fault_id": fault_id,
                                "rule": rule["name"], "brick_class": rule["brick_class_target"],
                                "device_id": dev["id"], "property_id": dev["property_id"],
                                "location": dev.get("location"), "severity": rule["severity"],
                                "status": "active", "detected_at": int(now.timestamp()),
                                "context": context,
                            })
                    else:
                        rid = await self.faults.resolve_fault(dev["id"], rule["id"])
                        if rid:
                            resolved += 1
                            await self.dispatcher.dispatch({
                                "event": "fault.resolved", "fault_id": rid, "rule": rule["name"],
                                "device_id": dev["id"], "property_id": dev["property_id"],
                                "status": "resolved", "resolved_at": int(now.timestamp()),
                            })
                except Exception as exc:  # noqa: BLE001
                    log.warning("device evaluation failed",
                                extra={"device": dev.get("id"), "rule": rule.get("id"),
                                       "error": str(exc)})

        summary = {"rules": len(rules), "devices_checked": checked,
                   "faults_opened": opened, "faults_resolved": resolved}
        log.info("evaluation cycle complete", extra=summary)
        return summary
