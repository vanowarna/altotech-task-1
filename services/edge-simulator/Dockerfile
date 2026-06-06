FROM python:3.11-slim

WORKDIR /app

COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY services/edge-simulator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/edge-simulator /app/edge-simulator
COPY deploy/topology.yaml /app/deploy/topology.yaml

WORKDIR /app/edge-simulator
CMD ["python", "simulator.py"]
