"""CSV replayer — streams AltoTech's real sample sensor data into the ingest API.

Maps the provided iot_sample_data CSVs onto the `hotel_live` devices, remapping the
recorded timestamps onto the recent wall-clock window so the AFDD engine and dashboard
treat them as a live feed. Backfills the last N minutes on startup, then streams live.

Mapping:
  sample_iaq_data_Room{101,102,103}.csv  cols temperature,humidity,co2
      -> hotel_live-r{101,102,103}-{temperature,humidity,co2}
  sample_presence_sensor_data_Room{101,102,103}.csv  col presence_state
      -> hotel_live-r{101,102,103}-occupancy
  sample_power_meter_data.csv  cols power_kw_power_meter_1..6
      -> hotel_live-f1-power{1..6}
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx

CSV_DIR = os.environ.get("CSV_DIR", "/data/csv")
API = os.environ.get("API_BASE_URL", "http://localhost:8000")
PUSH_INTERVAL = int(os.environ.get("REPLAY_INTERVAL_SECONDS", "15"))
BACKFILL_MIN = int(os.environ.get("REPLAY_BACKFILL_MINUTES", "30"))
ROOMS = ["101", "102", "103"]


def log(msg: str, **extra):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "logger": "csv-replayer", "msg": msg}
    rec.update(extra)
    print(json.dumps(rec), flush=True)


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        log("csv missing, skipping", path=path)
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_sources() -> dict[str, list[dict]]:
    """Return {source_key: rows}. Keys: iaq_101.., presence_101.., power."""
    sources: dict[str, list[dict]] = {}
    for room in ROOMS:
        sources[f"iaq_{room}"] = _read_csv(os.path.join(CSV_DIR, f"sample_iaq_data_Room{room}.csv"))
        sources[f"presence_{room}"] = _read_csv(
            os.path.join(CSV_DIR, f"sample_presence_sensor_data_Room{room}.csv"))
    sources["power"] = _read_csv(os.path.join(CSV_DIR, "sample_power_meter_data.csv"))
    return sources


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def frame_readings(sources: dict[str, list[dict]], idx: int, ts: int) -> list[dict]:
    """Build one batch of readings for tick `idx`, stamped `ts`."""
    out: list[dict] = []

    def add(device_id, datapoint, value):
        if value is not None and value != "":
            out.append({"device_id": device_id, "datapoint": datapoint,
                        "value": value, "timestamp": ts})

    for room in ROOMS:
        iaq = sources.get(f"iaq_{room}") or []
        if iaq:
            row = iaq[idx % len(iaq)]
            add(f"hotel_live-r{room}-temperature", "temperature", _num(row.get("temperature")))
            add(f"hotel_live-r{room}-humidity", "humidity", _num(row.get("humidity")))
            add(f"hotel_live-r{room}-co2", "co2", _num(row.get("co2")))
        pres = sources.get(f"presence_{room}") or []
        if pres:
            row = pres[idx % len(pres)]
            state = (row.get("presence_state") or "").strip().lower()
            if state:
                add(f"hotel_live-r{room}-occupancy", "occupancy", state)

    power = sources.get("power") or []
    if power:
        row = power[idx % len(power)]
        for n in range(1, 7):
            add(f"hotel_live-f1-power{n}", "power", _num(row.get(f"power_kw_power_meter_{n}")))
    return out


def push(client: httpx.Client, readings: list[dict]) -> None:
    if not readings:
        return
    try:
        r = client.post(f"{API}/api/v1/ingest/batch", json={"readings": readings}, timeout=30)
        body = r.json() if r.status_code < 300 else {}
        log("pushed", count=len(readings), accepted=body.get("accepted"),
            rejected=body.get("rejected"), status=r.status_code)
    except Exception as exc:  # noqa: BLE001
        log("push failed", error=str(exc))


def wait_for_api(client: httpx.Client, retries: int = 60) -> bool:
    for _ in range(retries):
        try:
            if client.get(f"{API}/ready", timeout=5).json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main() -> None:
    sources = load_sources()
    loaded = {k: len(v) for k, v in sources.items() if v}
    log("sources loaded", **loaded)
    if not loaded:
        log("no CSVs found; exiting", csv_dir=CSV_DIR)
        sys.exit(0)

    client = httpx.Client()
    if not wait_for_api(client):
        log("API never became ready; exiting")
        sys.exit(1)

    # Backfill: spread the most recent BACKFILL_MIN rows across the last N minutes.
    now = int(time.time())
    if BACKFILL_MIN > 0:
        log("backfill start", minutes=BACKFILL_MIN)
        for m in range(BACKFILL_MIN, 0, -1):
            ts = now - m * 60
            idx = max(0, (BACKFILL_MIN - m))
            push(client, frame_readings(sources, idx, ts))
        log("backfill done")

    # Live loop.
    idx = BACKFILL_MIN
    log("live loop start", interval_s=PUSH_INTERVAL)
    while True:
        ts = int(time.time())
        push(client, frame_readings(sources, idx, ts))
        idx += 1
        time.sleep(PUSH_INTERVAL)


if __name__ == "__main__":
    main()
