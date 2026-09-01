from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.opcua_control import OpcUaControlClient
from backend.schemas import AcknowledgeRequest, FaultCommand, LoadCommand, RunningCommand
from backend.websocket_manager import WebSocketManager
from common.db import Database
from common.settings import settings

logger = logging.getLogger("backend")
BASE_DIR = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = BASE_DIR / "dashboard"


async def broadcaster(app: FastAPI) -> None:
    db: Database = app.state.db
    manager: WebSocketManager = app.state.ws_manager
    last_telemetry_time: str | None = None
    last_alarm_signature: tuple[Any, ...] | None = None

    while True:
        try:
            latest = await db.latest_telemetry(settings.motor_id)
            if latest and latest.get("time") != last_telemetry_time:
                last_telemetry_time = str(latest.get("time"))
                await manager.broadcast({"type": "telemetry", "data": latest})

            alarms = await db.list_alarms(settings.motor_id, open_only=True, limit=100)
            signature = tuple(
                (a.get("id"), a.get("state"), a.get("severity"), a.get("last_seen_at"))
                for a in alarms
            )
            if signature != last_alarm_signature:
                last_alarm_signature = signature
                await manager.broadcast({"type": "alarms", "data": alarms})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("WebSocket broadcaster cycle failed: %s", exc)

        await asyncio.sleep(settings.websocket_poll_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    db = Database(settings.database_url)
    await db.connect()
    app.state.db = db
    app.state.ws_manager = WebSocketManager()
    app.state.opcua_control = OpcUaControlClient()
    task = asyncio.create_task(broadcaster(app))
    logger.info("Backend started for %s", settings.motor_id)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await db.close()


app = FastAPI(
    title="Industrial Predictive Maintenance Platform",
    version="1.0.0",
    description=(
        "OPC UA condition-monitoring lab with TimescaleDB historian, explainable "
        "anomaly detection, health scoring and alarm lifecycle management."
    ),
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/api/health")
async def api_health(request: Request) -> dict[str, Any]:
    db: Database = request.app.state.db
    latest = await db.latest_telemetry(settings.motor_id)
    return {
        "status": "ok" if await db.ping() else "degraded",
        "database": "connected" if await db.ping() else "unavailable",
        "motor_id": settings.motor_id,
        "latest_telemetry_time": latest.get("time") if latest else None,
        "websocket_clients": request.app.state.ws_manager.client_count,
    }


@app.get("/api/motors")
async def motors(request: Request) -> list[dict[str, Any]]:
    return await request.app.state.db.list_motors()


@app.get("/api/motors/{motor_id}/current")
async def current(motor_id: str, request: Request) -> dict[str, Any]:
    data = await request.app.state.db.latest_telemetry(motor_id)
    if data is None:
        raise HTTPException(status_code=404, detail="No telemetry found for motor")
    return data


@app.get("/api/motors/{motor_id}/history")
async def history(
    motor_id: str,
    request: Request,
    minutes: int = Query(default=60, ge=1, le=1440),
    limit: int = Query(default=1800, ge=10, le=5000),
) -> list[dict[str, Any]]:
    return await request.app.state.db.history(motor_id, minutes=minutes, limit=limit)


@app.get("/api/alarms")
async def alarms(
    request: Request,
    motor_id: str | None = None,
    open_only: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    return await request.app.state.db.list_alarms(
        motor_id=motor_id,
        open_only=open_only,
        limit=limit,
    )


@app.post("/api/alarms/{alarm_id}/ack")
async def acknowledge_alarm(
    alarm_id: int,
    body: AcknowledgeRequest,
    request: Request,
) -> dict[str, Any]:
    alarm = await request.app.state.db.acknowledge_alarm(
        alarm_id,
        body.acknowledged_by,
    )
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm not found")
    if alarm["state"] == "CLEARED":
        raise HTTPException(status_code=409, detail="Cleared alarms cannot be acknowledged")
    return alarm


@app.get("/api/simulation/state")
async def simulation_state(request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.opcua_control.read_state()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OPC UA control unavailable: {exc}") from exc


@app.post("/api/simulation/fault")
async def set_fault(body: FaultCommand, request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.opcua_control.set_fault(body.mode, body.intensity)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OPC UA control unavailable: {exc}") from exc


@app.post("/api/simulation/reset")
async def reset_simulation(request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.opcua_control.reset()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OPC UA control unavailable: {exc}") from exc


@app.post("/api/simulation/load")
async def set_load(body: LoadCommand, request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.opcua_control.set_target_load(body.target_load)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OPC UA control unavailable: {exc}") from exc


@app.post("/api/simulation/running")
async def set_running(body: RunningCommand, request: Request) -> dict[str, Any]:
    try:
        return await request.app.state.opcua_control.set_running(body.running)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OPC UA control unavailable: {exc}") from exc


@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket) -> None:
    manager: WebSocketManager = websocket.app.state.ws_manager
    db: Database = websocket.app.state.db
    await manager.connect(websocket)
    try:
        latest = await db.latest_telemetry(settings.motor_id)
        if latest:
            await websocket.send_json({"type": "telemetry", "data": latest})
        open_alarms = await db.list_alarms(settings.motor_id, open_only=True, limit=100)
        await websocket.send_json({"type": "alarms", "data": open_alarms})
        while True:
            # Browser does not need to send data. Receiving keeps disconnect detection immediate.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
