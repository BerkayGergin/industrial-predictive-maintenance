# REST and WebSocket API

Interactive OpenAPI documentation is available at `http://localhost:8000/docs` when the stack is running.

## Read endpoints

- `GET /api/health` — backend/database status and latest telemetry timestamp
- `GET /api/motors` — latest summary for each motor in the historian
- `GET /api/motors/Motor_01/current` — latest analyzed snapshot
- `GET /api/motors/Motor_01/history?minutes=60&limit=1800` — historian samples
- `GET /api/alarms?motor_id=Motor_01&open_only=true` — alarms
- `GET /api/simulation/state` — current writable OPC UA control values

## Commands

`POST /api/simulation/fault`

```json
{"mode":"BEARING_WEAR","intensity":1.0}
```

`POST /api/simulation/load`

```json
{"target_load":75}
```

Use `-1` for the automatic load profile.

`POST /api/simulation/running`

```json
{"running":false}
```

`POST /api/simulation/reset`

No request body is required.

`POST /api/alarms/{id}/ack`

```json
{"acknowledged_by":"operator"}
```

## WebSocket

`ws://localhost:8000/ws/telemetry`

Message envelopes:

```json
{"type":"telemetry","data":{}}
```

```json
{"type":"alarms","data":[]}
```
