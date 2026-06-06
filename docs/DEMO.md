# Live Demo Script

A ~10-minute walkthrough for the assessment review. Run it top to bottom.

## 0. Start the stack (before the call)
```bash
cd deploy
cp .env.example .env
docker compose up --build
```
Wait until logs show the engine's `evaluation cycle complete`. Then optionally run the
smoke test in another terminal:
```bash
python tests/integration/smoke_test.py
```

Open four tabs:
- Dashboard — http://localhost:8080
- Swagger — http://localhost:8000/docs
- Neo4j Browser — http://localhost:7474 (user `neo4j`, password from `.env`)
- (optional) terminal tailing `docker compose logs -f afdd-engine`

---

## 1. Frame the problem (30s)
"AltoTech scales from 60 to 400 properties. The platform answers one question —
*what equipment needs attention, and why* — across many sites, using Brick Schema so
the model is portable. Buildings are graphs, so I modeled them natively in Neo4j and
kept the high-volume readings in TimescaleDB."

## 2. Dashboard (1–2 min)
On http://localhost:8080:
- KPI tiles: active faults, by severity. Toggle **light/dark**, show it's **mobile**
  (resize). Point out it auto-refreshes.
- Severity doughnut + faults-by-property bar.
- The fault table: a **temperature excursion** (Hotel A 101), a **CO₂ flatline**
  (Hotel A 102), and an **energy anomaly** (Hotel C) once live data accrues.
- Click **Ack**, then **Resolve** on a fault — watch it update.

## 3. The Brick graph (2 min) — Neo4j Browser
Run these live to show topology is first-class:
```cypher
// the shape of one room
MATCH (p:Property)-[:hasPart]->(l:Location)-[:hasPoint]->(d:Device)-[:rdf_type]->(b:BrickClass)
RETURN p,l,d,b LIMIT 25;
```
```cypher
// "find all temperature sensors on Floor 2 of Hotel C" — a traversal, not a join
MATCH (p:Property {id:'hotel_c'})-[:hasPart]->(l:Location {floor:2})-[:hasPoint]->(d:Device)
MATCH (d)-[:rdf_type]->(:BrickClass {uri:'brick:Zone_Air_Temperature_Sensor'})
RETURN d.id;
```
```cypher
// a fault, its device, and the rule that raised it
MATCH (f:Fault)-[:detectedOn]->(d:Device), (f)-[:raisedBy]->(r:Rule)
RETURN f,d,r LIMIT 10;
```

## 4. Ingestion + resolution (1 min) — Swagger
On http://localhost:8000/docs:
- `POST /api/v1/ingest` with `{device_id, datapoint, value, timestamp}` — note the
  payload carries **no brick_class**; the response shows it was resolved from the graph.
- `GET /api/v1/devices?brick_class=brick:CO2_Sensor` — Brick-class query for external
  consumers (analytics/twins).

## 5. Rules are data (1–2 min) — Swagger
- `GET /api/v1/rules` — the 4 seeded rules; show `property_overrides` (Hotel A temp
  threshold 26 vs 28 elsewhere).
- `POST /api/v1/rules` with a new rule (e.g. high CO₂) — **no deploy**, it's live next
  cycle. (Schema lives in `skills/SKILL.md`.)
- Explain the engine loop: traverse Brick targets → window query → evaluate → open/
  resolve fault (dedup) → dispatch.

## 6. Close (30s)
- Where time-series lives and why (ADR-0002) — the boundary decision.
- Scale story: shard evaluation by property, graph stays small, Timescale continuous
  aggregates. New rule *types* via the evaluator plugin registry.
- AI-ready: export graph + rules + faults; the `SKILL.md` lets Claude generate valid
  rules.

## If something misbehaves
- No faults yet? The engine evaluates on `EVAL_INTERVAL_SECONDS` (default 60). Temp/
  flatline come from backfill immediately; energy is live-only. Lower the interval in
  `.env` for a snappier demo.
- Reset state: `docker compose down -v && docker compose up --build`.
