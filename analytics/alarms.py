from __future__ import annotations

from dataclasses import dataclass

from common.models import AnalyzedTelemetry


@dataclass(frozen=True, slots=True)
class AlarmCondition:
    code: str
    active: bool
    severity: str
    message: str
    value: float | None = None
    threshold: float | None = None
    unit: str | None = None


def evaluate_alarm_conditions(sample: AnalyzedTelemetry) -> list[AlarmCondition]:
    raw = sample.raw
    anomaly = sample.anomaly
    health = sample.health

    vibration_critical = raw.vibration >= 4.5
    bearing_critical = raw.bearing_temperature >= 82.0
    motor_temp_critical = raw.motor_temperature >= 100.0

    return [
        AlarmCondition(
            code="HIGH_VIBRATION",
            active=raw.vibration >= 2.5,
            severity="CRITICAL" if vibration_critical else "WARNING",
            message="Motor vibration exceeds the condition-monitoring limit.",
            value=raw.vibration,
            threshold=2.5,
            unit="mm/s",
        ),
        AlarmCondition(
            code="HIGH_BEARING_TEMPERATURE",
            active=raw.bearing_temperature >= 65.0,
            severity="CRITICAL" if bearing_critical else "WARNING",
            message="Bearing temperature is above the configured limit.",
            value=raw.bearing_temperature,
            threshold=65.0,
            unit="°C",
        ),
        AlarmCondition(
            code="HIGH_MOTOR_TEMPERATURE",
            active=raw.motor_temperature >= 80.0,
            severity="CRITICAL" if motor_temp_critical else "WARNING",
            message="Motor winding/body temperature is above the configured limit.",
            value=raw.motor_temperature,
            threshold=80.0,
            unit="°C",
        ),
        AlarmCondition(
            code="ANOMALY_DETECTED",
            active=anomaly.baseline_ready and anomaly.score >= 0.65,
            severity="CRITICAL" if anomaly.score >= 0.88 else "WARNING",
            message="Load-compensated telemetry deviates from the learned healthy baseline.",
            value=anomaly.score,
            threshold=0.65,
            unit="score",
        ),
        AlarmCondition(
            code="LOW_HEALTH_SCORE",
            active=health.score < 60,
            severity="CRITICAL",
            message="Combined machine health score has entered the critical range.",
            value=float(health.score),
            threshold=60.0,
            unit="score",
        ),
    ]
