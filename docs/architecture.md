# Architecture

## Goal

This repository is an industrial condition-monitoring and predictive-maintenance **lab prototype**. It is intentionally divided into services that mirror common OT/IT boundaries rather than putting the entire demo in one Python process.

```text
Motor physics + fault injection
        |
        | OPC UA server (4840)
        v
Subscription Collector
        |
        | 1 s analyzed snapshots
        v
Anomaly + Health + Alarm Pipeline
        |
        | SQL
        v
TimescaleDB / PostgreSQL
        |
        +--------------------------+
        |                          |
        v                          v
FastAPI REST                 WebSocket broadcaster
        |                          |
        +------------+-------------+
                     v
               Browser dashboard

FastAPI also writes simulation controls back to the OPC UA server.
```

## Service responsibilities

### `simulator`
- Owns the motor state and simplified physics.
- Publishes electrical, mechanical and thermal variables through OPC UA.
- Exposes writable simulation control nodes.
- Does **not** calculate downstream anomaly or health scores.

### `collector`
- Connects as an OPC UA client.
- Discovers the namespace index from the namespace URI.
- Creates a Subscription and Monitored Items instead of polling each sensor with repeated reads.
- Keeps the newest values and creates one coherent historian snapshot per second.
- Runs explainable analytics and reconciles persistent alarms.

### `database`
- TimescaleDB on PostgreSQL 17.
- `telemetry` is a hypertable.
- `alarms` stores lifecycle state separately from telemetry.
- `analytics_state` preserves the anomaly baseline across collector restarts.

### `backend`
- REST API for current state, history, alarms and simulator commands.
- WebSocket endpoint pushes telemetry and alarm changes to the browser.
- Uses OPC UA Write for simulation controls.
- Serves the static dashboard.

## Important design decisions

### Why no MQTT here?
This project deliberately focuses on OPC UA information modelling, subscriptions, historian design and condition monitoring. Adding MQTT between the collector and database would increase components without improving the learning objectives of this specific lab.

### Why TimescaleDB?
Telemetry is time-series data. TimescaleDB keeps PostgreSQL semantics while adding hypertables and time-series optimizations, so alarm/configuration tables and historian data can live in one database.

### Why WebSocket if the backend still queries the database?
The browser does not poll live telemetry. The backend watches for a new historian row and pushes it to every connected WebSocket client. This keeps browser transport event-driven while preserving the database as the shared source of truth between separate containers.

### Why a frozen baseline?
A moving anomaly baseline can gradually learn a developing fault and make it appear normal. The lab learns an initial healthy baseline, freezes it, and persists it. This is easy to explain and demonstrates the concept without pretending to be a production ML prognostics model.

## Production gaps

This project is not a machinery protection system. A real deployment would normally add OPC UA certificate security, user/role authorization, managed secrets, redundant collectors, schema migrations, observability, backup/retention policies, calibrated sensor limits, real asset metadata and validation against labeled plant data.
