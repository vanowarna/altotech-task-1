"""Thin async Neo4j client wrapper with the queries shared across services."""

from __future__ import annotations

from typing import Any, Optional

from neo4j import AsyncGraphDatabase

try:
    from neo4j.exceptions import ConfigurationError
except ImportError:  # pragma: no cover
    ConfigurationError = Exception

from .config import Settings


class Neo4jClient:
    def __init__(self, settings: Settings):
        auth = (settings.neo4j_user, settings.neo4j_password)
        # Silence "relationship/property does not exist" notifications, which are
        # expected before any Fault nodes are created. Falls back gracefully on
        # older drivers that don't support the kwarg.
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri, auth=auth, notifications_min_severity="OFF"
            )
        except (TypeError, ValueError, ConfigurationError):
            self._driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=auth)

    async def close(self) -> None:
        await self._driver.close()

    async def verify(self) -> bool:
        await self._driver.verify_connectivity()
        return True

    async def run(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(cypher, **params)
            return [record.data() async for record in result]

    # --- Domain queries -------------------------------------------------

    async def resolve_device(self, device_id: str) -> Optional[dict[str, Any]]:
        """Resolve a device to its Brick class + location + property (ingestion)."""
        rows = await self.run(
            """
            MATCH (d:Device {id: $id})-[:rdf_type]->(b:BrickClass)
            MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
            RETURN b.uri AS brick_class, l.name AS location,
                   l.floor AS floor, p.id AS property_id, d.datapoint AS datapoint
            """,
            id=device_id,
        )
        return rows[0] if rows else None

    async def resolve_devices_bulk(self, device_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Resolve many devices in one round-trip (ingestion batch path)."""
        rows = await self.run(
            """
            UNWIND $ids AS did
            MATCH (d:Device {id: did})-[:rdf_type]->(b:BrickClass)
            MATCH (d)-[:hasLocation]->(l:Location)<-[:hasPart]-(p:Property)
            RETURN d.id AS device_id, b.uri AS brick_class, l.name AS location,
                   l.floor AS floor, p.id AS property_id, d.datapoint AS datapoint
            """,
            ids=device_ids,
        )
        return {r["device_id"]: r for r in rows}

    async def devices_by_brick_class(
        self,
        brick_class: str,
        property_id: Optional[str] = None,
        floor: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Traversal: all devices of a Brick class, optionally scoped."""
        rows = await self.run(
            """
            MATCH (p:Property)-[:hasPart]->(l:Location)-[:hasPoint]->(d:Device)
            MATCH (d)-[:rdf_type]->(b:BrickClass {uri: $brick_class})
            WHERE ($property_id IS NULL OR p.id = $property_id)
              AND ($floor IS NULL OR l.floor = $floor)
            RETURN d.id AS id, d.datapoint AS datapoint, b.uri AS brick_class,
                   d.unit AS unit, l.name AS location, l.floor AS floor,
                   p.id AS property_id
            ORDER BY p.id, l.floor, d.id
            """,
            brick_class=brick_class,
            property_id=property_id,
            floor=floor,
        )
        return rows
