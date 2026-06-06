// Neo4j schema — constraints & indexes for the Brick graph.
// Run once at startup (idempotent). Ensures O(1) device resolution at ingestion.

CREATE CONSTRAINT property_id IF NOT EXISTS
  FOR (p:Property) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT location_id IF NOT EXISTS
  FOR (l:Location) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT device_id IF NOT EXISTS
  FOR (d:Device) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT brickclass_uri IF NOT EXISTS
  FOR (b:BrickClass) REQUIRE b.uri IS UNIQUE;

CREATE CONSTRAINT rule_id IF NOT EXISTS
  FOR (r:Rule) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT fault_id IF NOT EXISTS
  FOR (f:Fault) REQUIRE f.id IS UNIQUE;

// Secondary indexes for traversal performance.
CREATE INDEX location_floor IF NOT EXISTS FOR (l:Location) ON (l.floor);
CREATE INDEX device_datapoint IF NOT EXISTS FOR (d:Device) ON (d.datapoint);
CREATE INDEX fault_status IF NOT EXISTS FOR (f:Fault) ON (f.status);
