# Operations Guide

## Start

```powershell
docker compose up --build
```

Open:
- Dashboard: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- OPC UA endpoint from host: `opc.tcp://127.0.0.1:4840/predictive-maintenance/server/`
- PostgreSQL/TimescaleDB from host: `127.0.0.1:5433`

## Useful logs

```powershell
docker compose logs -f simulator
docker compose logs -f collector
docker compose logs -f backend
```

## Smoke check

With the stack running:

```powershell
python scripts/smoke_check.py
```

## Reset historian completely

This deletes the Docker database volume and therefore all telemetry, alarms and learned baseline state:

```powershell
docker compose down -v
docker compose up --build
```

## Demo sequence

1. Start the stack.
2. Wait until the dashboard says `Healthy baseline ready` (about 30 seconds with defaults).
3. Open **Simulation Lab**.
4. Inject `BEARING_WEAR` at 100% intensity.
5. Watch fault progress rise gradually; vibration and bearing temperature follow.
6. Observe anomaly score and health score.
7. Open **Alarm Center** and acknowledge an active alarm.
8. Reset the fault; the physical variables recover gradually and the alarm eventually clears.
9. Open **Historical Trends** to review the event in TimescaleDB history.

## Common problems

### Port already in use
Change `OPCUA_HOST_PORT`, `DASHBOARD_HOST_PORT` or `POSTGRES_HOST_PORT` in `.env`.

### Dashboard opens but no telemetry
Check `docker compose logs -f collector`. The collector must connect to both OPC UA and PostgreSQL.

### Baseline never becomes ready
Confirm new rows are being created once per second. A full database reset also resets the baseline.

### Timescale init changes do not appear
Docker's `/docker-entrypoint-initdb.d` scripts run only for a new database volume. Use `docker compose down -v` only when you intentionally want to delete lab data.
