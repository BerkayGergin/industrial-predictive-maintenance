CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS telemetry (
    time                    TIMESTAMPTZ      NOT NULL,
    motor_id                TEXT             NOT NULL,
    voltage                 DOUBLE PRECISION NOT NULL,
    current                 DOUBLE PRECISION NOT NULL,
    power                   DOUBLE PRECISION NOT NULL,
    rpm                     DOUBLE PRECISION NOT NULL,
    load                    DOUBLE PRECISION NOT NULL,
    vibration               DOUBLE PRECISION NOT NULL,
    motor_temperature       DOUBLE PRECISION NOT NULL,
    bearing_temperature     DOUBLE PRECISION NOT NULL,
    ambient_temperature     DOUBLE PRECISION NOT NULL,
    running                 BOOLEAN          NOT NULL,
    operating_hours         DOUBLE PRECISION NOT NULL,
    fault_mode              TEXT             NOT NULL DEFAULT 'NONE',
    fault_progress          DOUBLE PRECISION NOT NULL DEFAULT 0,
    anomaly_score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    anomaly_baseline_ready  BOOLEAN          NOT NULL DEFAULT FALSE,
    health_score            SMALLINT         NOT NULL,
    health_state            TEXT             NOT NULL,
    analysis                JSONB            NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (motor_id, time)
);

SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS telemetry_motor_time_desc_idx
    ON telemetry (motor_id, time DESC);
CREATE INDEX IF NOT EXISTS telemetry_health_state_idx
    ON telemetry (health_state, time DESC);

CREATE TABLE IF NOT EXISTS alarms (
    id               BIGSERIAL PRIMARY KEY,
    motor_id         TEXT        NOT NULL,
    code             TEXT        NOT NULL,
    severity         TEXT        NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    message          TEXT        NOT NULL,
    state            TEXT        NOT NULL CHECK (state IN ('ACTIVE', 'ACKNOWLEDGED', 'CLEARED')),
    value            DOUBLE PRECISION,
    threshold        DOUBLE PRECISION,
    unit             TEXT,
    activated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at  TIMESTAMPTZ,
    acknowledged_by  TEXT,
    cleared_at       TIMESTAMPTZ,
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS alarms_one_open_per_code_idx
    ON alarms (motor_id, code)
    WHERE state <> 'CLEARED';
CREATE INDEX IF NOT EXISTS alarms_time_idx
    ON alarms (activated_at DESC);
CREATE INDEX IF NOT EXISTS alarms_state_idx
    ON alarms (state, activated_at DESC);

CREATE TABLE IF NOT EXISTS analytics_state (
    motor_id    TEXT PRIMARY KEY,
    state       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE telemetry IS 'TimescaleDB historian for analyzed motor telemetry.';
COMMENT ON TABLE alarms IS 'Persistent alarm lifecycle: ACTIVE -> ACKNOWLEDGED -> CLEARED.';
COMMENT ON TABLE analytics_state IS 'Persisted anomaly baseline state so collector restarts do not retrain from zero.';
