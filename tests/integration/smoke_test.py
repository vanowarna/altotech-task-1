"""End-to-end smoke test against a running stack (run after `docker compose up`).

Verifies the full path: graph loaded -> Brick query -> ingest+resolve -> data query
-> rules seeded -> AFDD faults detected -> fault actions -> dashboard aggregation.

Usage:
    python tests/integration/smoke_test.py            # uses http://localhost:8000
    API_BASE_URL=http://host:8000 python tests/integration/smoke_test.py

Exits non-zero on the first failure. Also importable as a pytest module.
"""

from __future__ import annotations

import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
PASS, FAIL = "\033[92mPASS\033[0m", "\033[91mFAIL\033[0m"
results: list[tuple[bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((ok, name))
    print(f"  [{PASS if ok else FAIL}] {name}{(' — ' + detail) if detail else ''}")
    return ok


def wait_ready(timeout: int = 120) -> bool:
    print(f"Waiting for API readiness at {BASE} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/ready", timeout=5)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def poll_faults(timeout: int = 150) -> list[dict]:
    """The engine evaluates on an interval; give it time to open faults."""
    print("Polling for AFDD faults (engine runs on an interval) ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/api/v1/faults", timeout=10)
            if r.status_code == 200 and len(r.json()) > 0:
                return r.json()
        except Exception:
            pass
        time.sleep(5)
    return []


def run() -> int:
    if not check("API ready", wait_ready()):
        return 1

    # 1. Properties loaded (3 hotels)
    props = httpx.get(f"{BASE}/api/v1/properties").json()
    check("3 properties loaded", len(props) == 3, f"{len(props)} found")

    # 2. Brick-class traversal returns devices
    temps = httpx.get(f"{BASE}/api/v1/devices",
                      params={"brick_class": "brick:Zone_Air_Temperature_Sensor"}).json()
    check("temperature sensors via Brick query", len(temps) >= 30, f"{len(temps)} found")

    # 3. Ingest a single reading; brick_class resolved from the graph
    dev = temps[0]["id"]
    ing = httpx.post(f"{BASE}/api/v1/ingest",
                     json={"device_id": dev, "datapoint": "temperature",
                           "value": 24.2, "timestamp": int(time.time())}).json()
    check("ingest single reading accepted", ing.get("accepted") == 1)

    # 4. Query latest reading back
    latest = httpx.get(f"{BASE}/api/v1/devices/{dev}/latest")
    check("query latest reading", latest.status_code == 200,
          latest.json().get("brick_class", "") if latest.status_code == 200 else "")

    # 5. Unknown device is rejected (resolution guard)
    bad = httpx.post(f"{BASE}/api/v1/ingest",
                     json={"device_id": "ghost", "datapoint": "temperature",
                           "value": 1, "timestamp": int(time.time())}).json()
    check("unknown device rejected", bad.get("rejected") == 1)

    # 6. Default rules seeded
    rules = httpx.get(f"{BASE}/api/v1/rules").json()
    check("default rules seeded (>=4)", len(rules) >= 4, f"{len(rules)} rules")

    # 7. Faults detected by the engine
    faults = poll_faults()
    check("AFDD faults detected", len(faults) > 0, f"{len(faults)} faults")
    kinds = {f.get("rule") for f in faults}
    check("temperature/flatline fault present",
          any("Temperature" in (k or "") or "Flatline" in (k or "") for k in kinds),
          ", ".join(sorted(k for k in kinds if k)))

    # 8. Fault actions: acknowledge then resolve
    if faults:
        fid = faults[0]["id"]
        ack = httpx.post(f"{BASE}/api/v1/faults/{fid}/ack").json()
        check("acknowledge fault", ack.get("status") == "acknowledged")
        res = httpx.post(f"{BASE}/api/v1/faults/{fid}/resolve").json()
        check("resolve fault", res.get("status") == "resolved")

    # 9. Dashboard aggregation
    summ = httpx.get(f"{BASE}/api/v1/dashboard/summary").json()
    check("dashboard summary shape",
          all(k in summ for k in ("totals", "by_property", "by_severity", "recent_faults")))

    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


# pytest entrypoint
def test_smoke():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
