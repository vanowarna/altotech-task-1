"""Fault Manager — creates, deduplicates, and resolves Fault nodes in the graph.

Fault lifecycle: detected -> active -> acknowledged -> resolved.
Dedup rule: never create a new fault while an open one exists for the same
(device, rule). Faults link to their device and rule via graph edges.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from afdd_shared.neo4j_client import Neo4jClient

log = logging.getLogger("afdd.fault_manager")

OPEN_STATUSES = ["detected", "active", "acknowledged"]


class FaultManager:
    def __init__(self, neo4j: Neo4jClient):
        self.neo4j = neo4j

    async def open_fault(
        self, device_id: str, rule_id: str, severity: str, context: dict
    ) -> str | None:
        """Create a fault if none is open for (device, rule). Returns fault id or None (deduped)."""
        fault_id = f"f_{uuid.uuid4().hex[:12]}"
        ts = int(datetime.now(timezone.utc).timestamp())
        rows = await self.neo4j.run(
            """
            MATCH (d:Device {id: $did})
            MATCH (r:Rule {id: $rid})
            WHERE NOT EXISTS {
                MATCH (f:Fault)-[:detectedOn]->(d)
                MATCH (f)-[:raisedBy]->(r)
                WHERE f.status IN $open
            }
            CREATE (nf:Fault {id: $fid, severity: $sev, status: 'active',
                              detected_at: $ts, context: $ctx})
            CREATE (nf)-[:detectedOn]->(d)
            CREATE (nf)-[:raisedBy]->(r)
            RETURN nf.id AS id
            """,
            fid=fault_id, did=device_id, rid=rule_id, sev=severity, ts=ts,
            ctx=json.dumps(context), open=OPEN_STATUSES,
        )
        if rows:
            log.info("fault opened", extra={"fault_id": rows[0]["id"], "device_id": device_id,
                                            "rule_id": rule_id, "severity": severity})
            return rows[0]["id"]
        return None  # deduped

    async def resolve_fault(self, device_id: str, rule_id: str) -> str | None:
        """Resolve any open fault for (device, rule) when the condition clears."""
        ts = int(datetime.now(timezone.utc).timestamp())
        rows = await self.neo4j.run(
            """
            MATCH (f:Fault)-[:detectedOn]->(d:Device {id: $did})
            MATCH (f)-[:raisedBy]->(r:Rule {id: $rid})
            WHERE f.status IN $open
            SET f.status = 'resolved', f.resolved_at = $ts
            RETURN f.id AS id
            """,
            did=device_id, rid=rule_id, ts=ts, open=OPEN_STATUSES,
        )
        if rows:
            log.info("fault resolved", extra={"fault_id": rows[0]["id"], "device_id": device_id,
                                              "rule_id": rule_id})
            return rows[0]["id"]
        return None
