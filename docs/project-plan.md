# Project Plan and Engineering Scope

## Product goal

Build a self-contained industrial predictive-maintenance **lab platform** that demonstrates a realistic OT-to-IT data path using OPC UA, a time-series historian, explainable analytics, persistent alarm lifecycle management, a live WebSocket dashboard, and Docker Compose.

The project should be understandable enough to explain in an internship review while still using architecture patterns that scale beyond a toy script.

## Functional requirements

1. Simulate one induction motor with coupled electrical, mechanical and thermal behaviour.
2. Expose motor telemetry through a structured OPC UA address space.
3. Use OPC UA Subscription + Monitored Items for acquisition.
4. Persist one analyzed snapshot per second to TimescaleDB.
5. Learn a healthy baseline and calculate an explainable anomaly score.
6. Calculate an explainable 0–100 health score and state.
7. Persist alarm lifecycle state: ACTIVE, ACKNOWLEDGED, CLEARED.
8. Support gradual fault injection through writable OPC UA control nodes.
9. Provide REST APIs for current values, history, alarms and simulation controls.
10. Push live telemetry/alarms to the browser using WebSocket.
11. Start the entire platform with one Docker Compose command.
12. Include tests, documentation and a smoke-check script.

## Non-functional requirements

- **Separation of concerns:** simulator, collector/analytics, database and web API are separate services.
- **Stable contracts:** OPC UA nodes use string NodeIds and clients resolve namespace index by URI.
- **Persistence:** telemetry, alarm state and learned baseline survive application-container restarts.
- **Explainability:** health/anomaly results include contributors rather than only a label.
- **Failure visibility:** services log connection failures and use Docker health checks where useful.
- **Reproducibility:** runtime dependency versions and TimescaleDB image are pinned.
- **Minimal external frontend dependencies:** dashboard charts use the browser Canvas API; no CDN is required.

## Service contracts

### Simulator -> Collector
Transport: OPC UA TCP

Contract: sensor/status nodes under `Motor_01`, updated every 250 ms by default.

### Collector -> Database
Transport: PostgreSQL protocol

Contract: one complete telemetry snapshot per second plus alarm lifecycle changes and analytics state.

### Database -> Backend
Transport: PostgreSQL protocol

Contract: database is the shared source of truth between separate containers.

### Backend -> Browser
Transport: HTTP REST + WebSocket

Contract: REST for queries/commands; WebSocket for live updates.

### Backend -> Simulator
Transport: OPC UA Write

Contract: only explicit writable nodes under `Motor_01.Controls` are changed.

## Analytics strategy

### Anomaly detector

Use a nominal dynamic model to compensate expected load/thermal behaviour, then learn a frozen healthy distribution of residuals. This is more meaningful than applying a z-score directly to raw temperature or current, because those values are expected to change with operating load.

### Health score

Use deterministic penalties for measurable degradation indicators. A health score is easier to audit than a hidden black-box model for a learning project.

### Alarm engine

Treat alarms as persisted process state, not UI decorations. The collector is the authority that activates, updates, escalates and clears alarms. The backend only acknowledges them.

## Fault model

- `BEARING_WEAR`: gradually raises vibration and bearing temperature.
- `MISALIGNMENT`: raises vibration, current draw and temperature while slightly reducing speed.
- `OVERLOAD`: forces a high-load operating region and increases electrical/thermal stress.
- `COOLING_FAILURE`: mainly raises thermal equilibrium temperatures.

Fault progression follows a first-order response rather than instantly changing measurements.

## Test strategy

### Unit tests
- Motor fault behaviour
- Anomaly baseline and abnormal deviation
- Analytics-state persistence serialization
- Health-state transition
- Alarm-rule activation/severity

### Static validation
- Compile every Python source file.
- Validate JavaScript syntax.
- Validate Docker Compose/YAML structure.

### Runtime smoke test
After Docker starts, `scripts/smoke_check.py` checks API health and confirms that current telemetry exists.

## Deliberate exclusions

The first final version does not include MQTT, Kafka, Kubernetes, Redis, Grafana, neural networks or Remaining Useful Life prediction. Those would add technologies without improving the specific learning objectives. They can be added later as separate architecture exercises.
