# Running the System

## One-command startup
```bash
cd deploy
cp .env.example .env
docker compose up --build
```
Seeds 4 properties (143 devices), default AFDD rules, a backfill of history with embedded
faults, then evaluates rules continuously.

## URLs
| URL | What |
|---|---|
| http://localhost:8080 | 3D Fault Console (light/dark; hover a room for live readings) |
| http://localhost:8000/docs | Swagger UI (OpenAPI) |
| http://localhost:8000/health | Liveness · `/ready` readiness · `/metrics` Prometheus |
| http://localhost:7474 | Neo4j Browser (user `neo4j`, pass from `.env`) |

## Verify end-to-end
```bash
python tests/integration/smoke_test.py
```

## Tests
```bash
pip install -r requirements-dev.txt
./scripts/run_tests.sh        # 27 unit tests, each service in its own process
```

## Demo speed
Defaults use a fast preset (`EVAL_INTERVAL_SECONDS=15`). Set `60` in `deploy/.env` for
production-realistic timing. Full walkthrough:
[`docs/DEMO.md`](https://github.com/vanowarna/altotech-task-1/blob/main/docs/DEMO.md).
