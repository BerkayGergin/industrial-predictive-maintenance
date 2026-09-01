from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RawTelemetry:
    motor_id: str
    time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voltage: float = 0.0
    current: float = 0.0
    power: float = 0.0
    rpm: float = 0.0
    load: float = 0.0
    vibration: float = 0.0
    motor_temperature: float = 0.0
    bearing_temperature: float = 0.0
    ambient_temperature: float = 25.0
    running: bool = False
    operating_hours: float = 0.0
    fault_mode: str = "NONE"
    fault_progress: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["time"] = self.time.isoformat()
        return data


@dataclass(slots=True)
class AnomalyResult:
    score: float
    baseline_ready: bool
    z_scores: dict[str, float]
    feature_values: dict[str, float]


@dataclass(slots=True)
class HealthResult:
    score: int
    state: str
    contributors: list[dict[str, Any]]
    recommendation: str


@dataclass(slots=True)
class AnalyzedTelemetry:
    raw: RawTelemetry
    anomaly: AnomalyResult
    health: HealthResult

    def to_dict(self) -> dict[str, Any]:
        data = self.raw.to_dict()
        data.update(
            {
                "anomaly_score": round(self.anomaly.score, 4),
                "anomaly_baseline_ready": self.anomaly.baseline_ready,
                "health_score": self.health.score,
                "health_state": self.health.state,
                "analysis": {
                    "z_scores": self.anomaly.z_scores,
                    "feature_values": self.anomaly.feature_values,
                    "contributors": self.health.contributors,
                    "recommendation": self.health.recommendation,
                },
            }
        )
        return data
