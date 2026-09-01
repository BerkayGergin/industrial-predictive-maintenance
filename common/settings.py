from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    motor_id: str = os.getenv("MOTOR_ID", "Motor_01")
    namespace_uri: str = os.getenv(
        "OPCUA_NAMESPACE_URI", "urn:factory:predictive-maintenance"
    )
    opcua_server_endpoint: str = os.getenv(
        "OPCUA_SERVER_ENDPOINT",
        "opc.tcp://0.0.0.0:4840/predictive-maintenance/server/",
    )
    opcua_url: str = os.getenv(
        "OPCUA_URL",
        "opc.tcp://127.0.0.1:4840/predictive-maintenance/server/",
    )
    simulation_tick_seconds: float = _env_float("SIMULATION_TICK_SECONDS", 0.25)
    collector_publish_ms: int = _env_int("COLLECTOR_PUBLISH_MS", 500)
    collector_sampling_ms: int = _env_int("COLLECTOR_SAMPLING_MS", 250)
    collector_snapshot_seconds: float = _env_float("COLLECTOR_SNAPSHOT_SECONDS", 1.0)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://predictive:CHANGE_ME@127.0.0.1:5432/predictive",
    )
    baseline_samples: int = _env_int("ANOMALY_BASELINE_SAMPLES", 30)
    websocket_poll_seconds: float = _env_float("WEBSOCKET_POLL_SECONDS", 0.5)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    expose_simulator_truth: bool = _env_bool("EXPOSE_SIMULATOR_TRUTH", True)


settings = Settings()
