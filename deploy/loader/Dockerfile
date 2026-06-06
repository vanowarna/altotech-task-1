# One-shot init container: loads the Brick graph into Neo4j, then exits.
FROM python:3.11-slim

WORKDIR /app

COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY graph /app/graph
COPY deploy/topology.yaml /app/deploy/topology.yaml

CMD ["python", "graph/load_topology.py", "--topology", "deploy/topology.yaml"]
