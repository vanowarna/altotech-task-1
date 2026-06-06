# AI-Ready Design

How the platform exports its graph, data, and configs for AI analysis, and the data
formats that let an AI tool (e.g. Claude) discover and propose new AFDD rules.

## 1. What an AI needs, and how we expose it

| AI need | Export | Source |
|---|---|---|
| Building structure + semantics | Brick graph as JSON (nodes + edges, Brick classes) | `GET /api/v1/graph/export?property=` (traversal already implemented) |
| Historical behaviour | time-series windows / hourly aggregates per device | `GET /api/v1/devices/{id}/readings`, `readings_hourly` view |
| Current rules | rule configs as JSON | `GET /api/v1/rules` |
| Outcomes | fault records with context + Brick class | `GET /api/v1/faults` |

Everything is JSON over the documented `/api/v1` OpenAPI contract, so an AI agent
consumes the same API as any other client.

## 2. Format for AI rule suggestions

Rules already are a compact, machine-writable DSL — the exact object an AI emits:

```json
{
  "name": "High CO2 in occupied rooms",
  "brick_class_target": "brick:CO2_Sensor",
  "condition_type": "threshold_exceeded",
  "params": { "threshold_value": 1000, "comparison": ">",
              "duration_minutes": 15, "window_minutes": 20 },
  "severity": "warning",
  "property_overrides": { "hotel_c": { "threshold_value": 800 } }
}
```

An AI is given: the Brick class vocabulary (the typed nodes it can target), the
registered `condition_type`s and their `params` schemas (`afdd_shared/rules.py` +
`CONDITION_TYPES`), and recent readings/faults. It returns a rule JSON that is
validated and `POST`ed to `/api/v1/rules` — no code change, immediately live. The
bonus **`skills/SKILL.md`** packages exactly this knowledge for Claude.

## 3. Cross-site learnings for AI consumption

Structure fleet learnings as Brick-keyed records so they transfer across buildings:

```json
{
  "pattern": "co2_flatline_cluster",
  "brick_class": "brick:CO2_Sensor",
  "evidence": { "sites_affected": 7, "common_floor": 2, "window": "2026-W23" },
  "suggested_rule": { "condition_type": "flatline",
                      "params": { "window_minutes": 30, "min_stddev": 0.01 } }
}
```

Because the unit of learning is a **Brick class**, a rule learned on Hotel C applies
unchanged to Hotel A's `CO2_Sensor`s. This is the foundation for future AI-driven rule
discovery and cross-site learning called for in the assessment.

## 4. Feedback loop
`readings/aggregates + rules + faults → AI → candidate rules → /api/v1/rules → new
faults → …` closes the loop: the AI proposes, the engine validates against live data,
and operators promote what works.
