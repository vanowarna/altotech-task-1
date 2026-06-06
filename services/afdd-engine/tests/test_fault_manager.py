"""Regression guard for the Fault Manager Cypher.

Catches the class of bug where a query references a `$param` that the call site
never supplies (Neo4j raises ParameterMissing at runtime). Uses a fake Neo4j
client, so it needs no database — it would have caught the missing `fid` bug.
"""

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.fault_manager import FaultManager  # noqa: E402


class FakeNeo4j:
    """Records (cypher, params) and returns a confirming row."""

    def __init__(self):
        self.calls = []

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return [{"id": "f_test"}]


def _referenced_params(cypher: str) -> set[str]:
    # $param tokens, excluding Cypher's $$ escapes (none used here).
    return set(re.findall(r"\$(\w+)", cypher))


def test_open_fault_supplies_every_referenced_param():
    fake = FakeNeo4j()
    fm = FaultManager(fake)
    asyncio.run(fm.open_fault("dev1", "rule1", "warning", {"detail": 1}))
    cypher, params = fake.calls[-1]
    missing = _referenced_params(cypher) - set(params)
    assert not missing, f"open_fault Cypher references unsupplied params: {missing}"


def test_resolve_fault_supplies_every_referenced_param():
    fake = FakeNeo4j()
    fm = FaultManager(fake)
    asyncio.run(fm.resolve_fault("dev1", "rule1"))
    cypher, params = fake.calls[-1]
    missing = _referenced_params(cypher) - set(params)
    assert not missing, f"resolve_fault Cypher references unsupplied params: {missing}"


def test_open_fault_returns_id_on_create():
    fm = FaultManager(FakeNeo4j())
    fid = asyncio.run(fm.open_fault("dev1", "rule1", "warning", {}))
    assert fid == "f_test"
