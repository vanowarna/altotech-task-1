# Integration / smoke test

End-to-end verification against a **running** stack. Brings nothing up itself — start
the stack first, then run this to confirm the whole pipeline works.

```bash
# 1. start everything
cd deploy && docker compose up --build -d

# 2. run the smoke test (from repo root)
pip install httpx
python tests/integration/smoke_test.py
```

It checks, in order:
1. API readiness (`/ready` reports both Neo4j + TimescaleDB healthy)
2. 3 properties loaded into the graph
3. Brick-class traversal returns temperature sensors
4. single ingest is accepted (Brick class resolved from the graph)
5. latest reading queryable
6. unknown device is rejected (resolution guard)
7. default AFDD rules seeded
8. AFDD engine has detected faults (polls up to ~2.5 min for an evaluation cycle)
9. acknowledge → resolve a fault
10. dashboard summary returns the expected shape

Exits `0` only if every check passes. Override the target with
`API_BASE_URL=http://host:8000`.

> Note: faults from the temperature spike and CO₂ flatline appear on the first
> evaluation cycle (they're present in the 2-hour backfill). The energy anomaly is
> live-only by design, so it surfaces after a few minutes of live data.
