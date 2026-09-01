# Database Schema

## `telemetry`

TimescaleDB hypertable containing one analyzed motor snapshot per historian interval.

Important groups:

- Timestamp/asset: `time`, `motor_id`
- Electrical: `voltage`, `current`, `power`
- Mechanical: `rpm`, `load`, `vibration`
- Thermal: `motor_temperature`, `bearing_temperature`, `ambient_temperature`
- Status: `running`, `operating_hours`
- Lab ground truth: `fault_mode`, `fault_progress`
- Analytics: `anomaly_score`, `anomaly_baseline_ready`, `health_score`, `health_state`, `analysis`

The `analysis` JSONB field preserves detailed z-scores, health contributors and the recommendation without making every explanatory field a dedicated SQL column.

## `alarms`

Persistent alarm instances. Each activation creates a new row; an open alarm is updated until it clears.

The partial unique index guarantees at most one non-cleared alarm for each `(motor_id, code)` pair.

## `analytics_state`

Stores serialized anomaly-engine state per motor so collector restarts do not discard the learned baseline.
