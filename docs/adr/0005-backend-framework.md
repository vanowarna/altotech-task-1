# ADR-0005 — Backend Framework: FastAPI

**Status:** Accepted · **Date:** 2026-06-06

## Context
We need an HTTP service for ingestion, data query, rule management, and fault management. Required deliverables include an **OpenAPI/Swagger UI** and clean, testable, production-quality code.

## Decision
Use **FastAPI** (Python 3.11) with **Pydantic** models and **Uvicorn**.

## Alternatives considered
- **Django + DRF.** Batteries-included and present in AltoTech's reference stack, but heavier and more boilerplate for a focused microservice; Swagger needs extra wiring; ORM is geared to relational, while our stores are Neo4j + TimescaleDB (we use neo4j driver + asyncpg directly).
- **Flask.** Lightweight but no native async, no built-in schema/OpenAPI generation.

## Consequences
- **+** Auto-generated, always-accurate OpenAPI/Swagger at `/docs` (a required deliverable, free).
- **+** Async I/O suits the ingestion write path and concurrent DB calls; Pydantic gives strong request validation at the boundary.
- **+** Small surface area → fast to test and reason about; clean dependency-injection for DB clients.
- **−** Less "batteries-included" than Django (no built-in admin/ORM); acceptable since our persistence is non-relational/graph + hypertable.

## Scale path
Run multiple Uvicorn/Gunicorn workers behind an API gateway / load balancer; the service is stateless, so it scales horizontally; DB connection pooling via the shared clients package.
