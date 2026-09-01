from datetime import datetime, timezone

from analytics.alarms import evaluate_alarm_conditions
from common.models import AnalyzedTelemetry, AnomalyResult, HealthResult, RawTelemetry


def analyzed(vibration=1.0, bearing=45, motor=60, anomaly_score=0.1, health_score=95):
    raw = RawTelemetry(
        motor_id="Motor_01",
        time=datetime.now(timezone.utc),
        voltage=400,
        current=8,
        power=5,
        rpm=1460,
        load=55,
        vibration=vibration,
        motor_temperature=motor,
        bearing_temperature=bearing,
        ambient_temperature=25,
        running=True,
        operating_hours=1000,
    )
    anomaly = AnomalyResult(
        score=anomaly_score,
        baseline_ready=True,
        z_scores={},
        feature_values={},
    )
    health = HealthResult(
        score=health_score,
        state="CRITICAL" if health_score < 60 else "HEALTHY",
        contributors=[],
        recommendation="",
    )
    return AnalyzedTelemetry(raw=raw, anomaly=anomaly, health=health)


def test_alarm_rule_activation():
    conditions = {c.code: c for c in evaluate_alarm_conditions(analyzed(vibration=3.1))}
    assert conditions["HIGH_VIBRATION"].active
    assert conditions["HIGH_VIBRATION"].severity == "WARNING"


def test_critical_alarm_rule():
    conditions = {c.code: c for c in evaluate_alarm_conditions(analyzed(vibration=4.8, health_score=45))}
    assert conditions["HIGH_VIBRATION"].severity == "CRITICAL"
    assert conditions["LOW_HEALTH_SCORE"].active
