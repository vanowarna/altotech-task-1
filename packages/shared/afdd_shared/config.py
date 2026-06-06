"""Environment-driven configuration, shared by all services."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class Settings:
    # Neo4j
    neo4j_uri: str = _env("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user: str = _env("NEO4J_USER", "neo4j")
    neo4j_password: str = _env("NEO4J_PASSWORD", "altotech123")

    # TimescaleDB (Postgres)
    ts_host: str = _env("TS_HOST", "timescaledb")
    ts_port: int = int(_env("TS_PORT", "5432"))
    ts_db: str = _env("TS_DB", "afdd")
    ts_user: str = _env("TS_USER", "afdd")
    ts_password: str = _env("TS_PASSWORD", "afdd123")

    # API
    api_base_url: str = _env("API_BASE_URL", "http://api:8000")
    log_level: str = _env("LOG_LEVEL", "INFO")
    env: str = _env("ENV", "dev")

    @property
    def ts_dsn(self) -> str:
        return (
            f"postgresql://{self.ts_user}:{self.ts_password}"
            f"@{self.ts_host}:{self.ts_port}/{self.ts_db}"
        )


def get_settings() -> Settings:
    return Settings()
