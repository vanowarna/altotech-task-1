# Interview Speaking Notes — AltoTech AFDD (rehearse from this)

Panel: **Jay (CAIO)** + **Eyp (Director of Software Engineering)**, HR (Kanignan) at the end.
They grade **clarity of thinking, technical ownership, and judgment** — not slides.
Format: Visual walkthrough (10–15) · Live demo (10–15) · Technical discussion (30).

---

## ⏱️ 1.5-hour prep plan (do in this order)

1. **0–10 min — Start the stack.** In Codespaces: `cd deploy && docker compose up --build -d`.
   While it builds, read this file top to bottom once.
2. **10–20 min — Capture screenshots** (see `presentation/screenshots/README.md`) as a backup.
3. **20–35 min — Rehearse the 3 diagrams out loud** (architecture, Brick model + worked
   example, fault flow). Say them from memory twice. This is the highest-value 15 minutes.
4. **35–55 min — Do one full live-demo dry run** (the "Demo run order" below), timing it.
5. **55–75 min — Read `FUNDAMENTALS-QA.md` + `docs/interview-defense.md`** once each; say the
   answers to the storage-boundary, scaling, and "what would you change" questions out loud.
6. **75–85 min — The honesty story** (AI usage + your path) — rehearse it once, in your words.
7. **85–90 min — Buffer.** Confirm the demo is still up; open the 3 tabs (dashboard, Neo4j, Swagger).

**Tests:** run with `./scripts/run_tests.sh` → **27 passing** (each service in its own process). Bare `pytest` at root isn't used — each service has its own `app` package; the live smoke test now **skips by default** (run it with `RUN_SMOKE=1` only when the stack is up). Say this if they ask.

**Golden rule:** speak in plain sentences, pause, and if you don't know something say
*"I didn't implement that in the POC — here's how I'd approach it."* Ownership > bluffing.

---

## 🎯 Your story (say it naturally, ~60–90s)

> "I started by reading the brief myself. I hadn't heard the term **AFDD** before, so I looked
> up each concept — Brick Schema, fault detection — until I understood what the platform is
> really for: answering *what equipment needs attention, and why*, across many buildings.
>
> Then I broke it down into an architecture. With AI help I first sketched a full
> **production-grade** design, but that's heavier than a take-home needs — a message queue, a
> distributed scheduler, managed databases. So I **compressed it into a demo-scale version**
> that keeps the same shape and boundaries, but runs free with one command. I built it in
> **GitHub Codespaces** so it's reproducible anywhere.
>
> I used AI as a pair-programmer for boilerplate and syntax, but I **owned the design
> decisions** — the graph-vs-time-series split, the Brick model, the rule engine — and I
> validated everything with tests and by running it end to end."

That last paragraph is your **AI honesty line**. Deliver it calmly and it reads as maturity.

---

## 🧠 The 3 diagrams (know these cold)

### 1) System architecture (C4 container level)
Say it as a pipeline, left to right, naming the tech on each box:
- **Edge** — Python edge-simulator (3 hotels) + CSV replayer (real sample data) → push readings.
- **Ingestion API** — **FastAPI**; resolves each device against the graph, writes the reading.
- **Graph DB** — **Neo4j**; building topology + Brick semantics + rules + faults.
- **Time-series DB** — **TimescaleDB**; the high-volume readings hypertable.
- **AFDD engine** — Python + APScheduler; scheduler → evaluator → fault manager → dispatcher.
- **Dashboard** — nginx + Three.js/Chart.js single-page console.
One line: *"Edge → API (Brick resolution) → TimescaleDB → engine (traverse + evaluate) → Fault in Neo4j → dashboard/alerts."*

### 2) Brick data model + the worked example (they WILL ask this)
- Nodes: `Property → Location → Device`(a point), typed by `BrickClass`; plus `Rule`, `Fault`.
- Edges: `hasPart`, `hasPoint`, `hasLocation`, `rdf_type`, `targets`, `detectedOn`, `raisedBy`.
- **Worked example — "given a fault on a point, what's affected and why":**
  > Fault `f_x` `-[:detectedOn]->` Device `hotel_a-r101-temperature`.
  > Traverse `-[:hasLocation]->` **Room 101** `<-[:hasPart]-` **Hotel A** → that's **WHERE**.
  > Traverse `-[:raisedBy]->` Rule **"High Temperature Alert"** → that's **WHY** (>28 °C for 10 min).
  > The point's Brick class (`Zone_Air_Temperature_Sensor`) is **WHAT**.
- **Honest note on Equipment:** the sample data is room-level points, so I model to
  Location/Property. Equipment (e.g. the room's FCU/AHU) is **one more hop** via `isPointOf` —
  it's in the schema design; I didn't populate Equipment nodes because the provided data doesn't
  include them. *(Say this proactively — it shows judgment.)*

### 3) Fault-detection flow (reading → surfaced fault)
1. Sensor reading arrives at `POST /ingest` (only `device_id, datapoint, value, timestamp`).
2. API looks the device up in Neo4j → attaches Brick class + room + hotel.
3. Reading is written to TimescaleDB.
4. Engine wakes on a timer → for each rule, graph-traverses target devices by Brick class.
5. Pulls their recent window from TimescaleDB → applies the rule.
6. If tripped and no open fault → creates a `Fault` node (deduped), logs + webhooks.
7. Dashboard reads it → the room turns red, activity log shows it. Operator can ack/resolve.

---

## 🧩 Design choices — "since this is a demo, I did X instead of Y"

Say these as deliberate trade-offs, not shortcuts:
- **Neo4j Community (not Aura/cluster)** — same model + best browser for demoing; HA is an ops upgrade.
- **TimescaleDB self-hosted (not managed)** — identical engine locally, zero cost.
- **APScheduler in-process (not Celery/Temporal)** — no broker to run; engine is stateless so it's swappable.
- **Webhook + log alerts (not a queue → email/SMS/PagerDuty)** — adapter pattern; real channel is ~30 lines.
- **HTTP ingest (not Kafka/MQTT)** — simple + debuggable at POC volume; contract unchanged behind a broker.
- **Docker Compose (not Kubernetes)** — one-command startup; k8s manifests included as the path.
- **No auth (POC)** — out of scope for a detection POC; production = OIDC + RBAC + per-tenant keys.

**On the 3D UI (say this):** my first dashboard was a **textual/table** view of faults — correct
but flat. I personally prefer **graphical** representations, and I'd seen AltoTech do similar
building-visualization work, so I added a **Three.js live building map** — rooms colored by their
worst active fault, hover for live readings. It turns a fault list into an operations view.

**How I used the given data:** the 3 synthetic hotels are driven by a simulator with injected
faults for guaranteed demo coverage; the provided **`iot_sample_data` CSVs** are replayed into a
4th "Hotel D — Live Data" property, so the platform also runs on **real recordings**.

---

## 🎬 Demo run order (10–15 min, rehearse once)

1. **One command:** show `docker compose up` already running (or `docker compose ps` → all healthy).
2. **Dashboard** (`:8080`): KPIs (143 devices, healthy vs faulted, ingest/s), the **3D building map**
   — orbit it, **hover a room** to show live temp/humidity/CO₂, point at a red room.
3. **Activity log**: a temperature excursion + flatline + energy anomaly; click **Ack → Resolve**.
4. **Neo4j Browser** (`:7474`): run `MATCH (f:Fault)-[:detectedOn]->(d)-[:hasLocation]->(l)<-[:hasPart]-(p), (f)-[:raisedBy]->(r) RETURN * LIMIT 5` → show the worked example live.
5. **Swagger** (`:8000/docs`): `POST /ingest` (no brick_class in payload) and `GET /rules` (show property_overrides).
6. **Tests** (optional): `./scripts/run_tests.sh` → 27 passing.

**Backup:** screenshots you HAVE — dashboard, 3D map, room hover, compose-up, tests (in `presentation/screenshots/`). You do **not** have Neo4j / Swagger screenshots — show those **live** if the stack is up; if not, just describe them (that's fine).

---

## 💬 Technical discussion — one-liners (details in FUNDAMENTALS-QA.md)

- **DB choice / trade-offs:** graph for topology + semantics, time-series for the firehose, joined by `device_id`.
- **Scalability:** shard evaluation by `property_id`; graph stays small (readings aren't in it); Timescale chunking/aggregates.
- **Observability:** structured JSON logs, `/health` + `/ready`, `/metrics` (Prometheus).
- **Failure recovery:** engine is stateless; per-device `try/except`; dedup in DB so retries are safe; healthchecks gate startup.
- **Security:** POC has none; production = gateway + OIDC + RBAC + secrets manager + TLS.
- **Testing:** 27 unit tests (pure logic) + a DB-free regression guard + a live smoke test + CI (per-service).
- **Production-readiness gaps (say proactively):** auth, a real alert channel/queue, distributed scheduler, Equipment nodes, backpressure on ingest, and load tests.

---

## ✅ Mindset
You built this, you understand it, you can defend the trade-offs. Be calm, concrete, and honest
about the demo-vs-production line. That's exactly what they're evaluating.
