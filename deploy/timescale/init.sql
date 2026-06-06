-- TimescaleDB initialization — the high-volume readings store.
-- Runs automatically on first container start (mounted to docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS readings (
    time        TIMESTAMPTZ      NOT NULL,
    device_id   TEXT             NOT NULL,
    property_id TEXT             NOT NULL,
    brick_class TEXT             NOT NULL,
    datapoint   TEXT             NOT NULL,
    value       DOUBLE PRECISION,            -- numeric value (temp, co2, power, occupancy 0/1)
    value_text  TEXT                         -- categorical state (e.g. "occupied")
);

-- Convert to a hypertable partitioned by time (the core Timescale feature).
SELECT create_hypertable('readings', 'time', if_not_exists => TRUE);

-- Indexes matching the AFDD query patterns.
CREATE INDEX IF NOT EXISTS idx_readings_device_time
    ON readings (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_readings_prop_class_time
    ON readings (property_id, brick_class, time DESC);

-- Continuous aggregate: hourly stats per device, used for rolling-average rules
-- (e.g. Energy Anomaly vs. 7-day average). Cheap to query at scale.
CREATE MATERIALIZED VIEW IF NOT EXISTS readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    device_id,
    property_id,
    brick_class,
    avg(value)  AS avg_value,
    max(value)  AS max_value,
    min(value)  AS min_value,
    count(*)    AS samples
FROM readings
GROUP BY bucket, device_id, property_id, brick_class
WITH NO DATA;

-- Refresh policy keeps the aggregate current (skip if policy already exists).
SELECT add_continuous_aggregate_policy('readings_hourly',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);
