"""afdd_shared — shared library for the Multi-Site AFDD platform.

Single source of truth reused by the API, the AFDD engine, the edge simulator,
and the graph loader so that Brick mappings, topology, models, and DB clients
never drift between services.
"""

__version__ = "0.1.0"
