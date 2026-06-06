"""Edge simulator — simulates all 3 hotels' sensors and pushes to the ingestion API.

Configurable (config.yaml or env): push interval, sensor types (via topology),
seed, backfill window, and injected anomalies. Pushes batches to POST /ingest/batch.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "shared"))

from afdd_shared.logging_setup import setup_logging  # noqa: E402
from afdd_shared.topology import all_devices, load_topology, topology_summary  # noqa: E402

import generators as gen  # noqa: E402

log = setup_logging(os.environ.get("LOG_LEVEL", "INFO"), "simulator")

FAR_FUTURE = 4102444800  # year 2100


def _start_for(kind: str, now: int) -> int:
    """Energy anomalies must be confined to recent time so they don't pollute their
    own rolling baseline; all others are active throughout (incl. backfill) so the
    corresponding faults surface immediately."""
    if kind == "energy_anomaly":
        return now - 600  # last ~10 minutes only
    return 0


def build_anomaly_map(cfg: dict, devices, seed: int, now: int | None = None) -> dict[str, gen.Anomaly]:
    """Bind anomalies to concrete device IDs from the simulator config."""
    now = now if now is not None else int(time.time())
    rng = random.Random(seed)
    amap: dict[str, gen.Anomaly] = {}
    for entry in cfg.get("anomalies", []):
        if not isinstance(entry, dict) or "kind" not in entry:
            continue
        suffix = entry.get("device_suffix")
        if not suffix:
            continue
        for d in devices:
            if d.id.endswith(suffix) or d.id == suffix:
                amap[d.id] = gen.Anomaly(kind=entry["kind"],
                                         start_ts=_start_for(entry["kind"], now), end_ts=FAR_FUTURE)
    # Random low-rate anomalies on other devices.
    random_rate = 0.0
    for entry in cfg.get("anomalies", []):
        if isinstance(entry, dict) and "random_rate" in entry:
            random_rate = float(entry["random_rate"])
    if random_rate:
        for d in devices:
            if d.id in amap:
                continue
            kind_by_dp = {
                "temperature": "temperature_spike",
                "power": "energy_anomaly",
                "occupancy": "schedule_violation",
            }
            kind = kind_by_dp.get(d.datapoint, "flatline")
            if rng.random() < random_rate:
                amap[d.id] = gen.Anomaly(kind=kind, start_ts=_start_for(kind, now), end_ts=FAR_FUTURE)
    return amap


def make_reading(device, ts: int, rng: random.Random, anomaly) -> dict:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    value, _meta = gen.reading_value(device.datapoint, dt, ts, rng, anomaly)
    return {"device_id": device.id, "datapoint": device.datapoint, "value": value, "timestamp": ts}


def push_batch(client: httpx.Client, base_url: str, readings: list[dict]) -> None:
    try:
        resp = client.post(f"{base_url}/api/v1/ingest/batch", json={"readings": readings}, timeout=30)
        if resp.status_code >= 300:
            log.warning("ingest non-2xx", extra={"status": resp.status_code, "body": resp.text[:200]})
        else:
            body = resp.json()
            log.info("pushed batch", extra={"count": len(readings),
                                            "accepted": body.get("accepted"),
                                            "rejected": body.get("rejected")})
    except Exception as exc:  # noqa: BLE001
        log.error("push failed", extra={"error": str(exc)})


def run(cfg: dict, topology_path: str, base_url: str) -> None:
    seed = int(cfg.get("seed", 42))
    props = load_topology(topology_path)
    exclude = set(cfg.get("exclude_properties", []))
    if exclude:
        props = [p for p in props if p.id not in exclude]
    devices = all_devices(props)
    log.info("topology loaded", extra={**topology_summary(props), "excluded": list(exclude)})
    anomalies = build_anomaly_map(cfg, devices, seed)
    log.info("anomalies bound", extra={"count": len(anomalies),
                                       "devices": list(anomalies.keys())[:10]})

    client = httpx.Client()

    # 1) Backfill historical readings so AFDD has immediate data.
    bf = cfg.get("backfill", {}) or {}
    bf_minutes = int(bf.get("minutes", 0))
    if bf_minutes > 0:
        step = int(bf.get("step_seconds", 60))
        now = int(time.time())
        start = now - bf_minutes * 60
        log.info("backfill start", extra={"minutes": bf_minutes, "step_s": step})
        t = start
        while t < now:
            rng = random.Random(seed + t)
            batch = [make_reading(d, t, rng, anomalies.get(d.id)) for d in devices]
            push_batch(client, base_url, batch)
            t += step
        log.info("backfill done")

    # 2) Live loop.
    interval = int(cfg.get("push_interval_seconds", 30))
    log.info("live loop start", extra={"interval_s": interval})
    while True:
        ts = int(time.time())
        rng = random.Random(seed + ts)
        batch = [make_reading(d, ts, rng, anomalies.get(d.id)) for d in devices]
        push_batch(client, base_url, batch)
        time.sleep(interval)


def main() -> None:
    here = Path(__file__).resolve().parent
    repo_root = here.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(here / "config.yaml"))
    parser.add_argument("--topology", default=os.environ.get(
        "TOPOLOGY_PATH", str(repo_root / "deploy" / "topology.yaml")))
    parser.add_argument("--api", default=os.environ.get("API_BASE_URL", "http://localhost:8000"))
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    run(cfg, args.topology, args.api)


if __name__ == "__main__":
    main()
