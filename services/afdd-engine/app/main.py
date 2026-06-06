"""AFDD engine entrypoint — schedules periodic rule evaluation (ADR-0004).

Stateless between runs: all state (rules, faults) lives in Neo4j, so the scheduler
is a swappable seam (APScheduler now; Celery/Temporal at scale).
"""

from __future__ import annotations

import asyncio
import os

from afdd_shared.config import get_settings
from afdd_shared.logging_setup import setup_logging
from afdd_shared.neo4j_client import Neo4jClient
from afdd_shared.timescale import TimescaleClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .dispatcher import AlertDispatcher
from .evaluator import AfddEvaluator
from .seed import seed_default_rules

log = setup_logging(os.environ.get("LOG_LEVEL", "INFO"), "afdd.main")

EVAL_INTERVAL = int(os.environ.get("EVAL_INTERVAL_SECONDS", "60"))
SEED_ON_START = os.environ.get("SEED_RULES", "true").lower() == "true"


async def _wait_for_deps(neo4j: Neo4jClient, ts: TimescaleClient, retries: int = 30) -> None:
    for attempt in range(retries):
        try:
            await neo4j.verify()
            await ts.ping()
            log.info("dependencies ready")
            return
        except Exception as exc:  # noqa: BLE001
            log.info("waiting for deps", extra={"attempt": attempt + 1, "error": str(exc)})
            await asyncio.sleep(2)
    raise RuntimeError("dependencies not ready")


async def main() -> None:
    settings = get_settings()
    neo4j = Neo4jClient(settings)
    ts = TimescaleClient(settings)
    await ts.connect()
    await _wait_for_deps(neo4j, ts)

    if SEED_ON_START:
        await seed_default_rules(neo4j)

    dispatcher = AlertDispatcher.from_env()
    evaluator = AfddEvaluator(neo4j, ts, dispatcher)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(evaluator.evaluate_all, "interval", seconds=EVAL_INTERVAL,
                      id="afdd_eval", max_instances=1, coalesce=True)
    scheduler.start()
    log.info("AFDD engine started", extra={"interval_s": EVAL_INTERVAL})

    # Run one cycle immediately so faults appear without waiting a full interval.
    # Guard it: a failed first cycle must not crash the engine — the scheduler keeps it alive.
    try:
        await evaluator.evaluate_all()
    except Exception as exc:  # noqa: BLE001
        log.error("initial evaluation cycle failed", extra={"error": str(exc)})

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):  # pragma: no cover
        scheduler.shutdown()
        await neo4j.close()
        await ts.close()


if __name__ == "__main__":
    asyncio.run(main())
