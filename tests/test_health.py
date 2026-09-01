from datetime import datetime, timezone

from analytics.health import HealthEngine
from common.models import AnomalyResult, RawTelemetry


def raw(vibration=1.1, bearing=48, motor=65, current=8.7, load=60):
    return RawTelemetry(
        motor_id="Motor_01",
        time=datetime.now(timezone.utc),
        voltage=400,
        current=current,
        power=5,
        rpm=1460,
        load=load,
        vibration=vibration,
        motor_temperature=motor,
        bearing_temperature=bearing,
        ambient_temperature=25,
        running=True,
        operating_hours=1000,
    )


def anomaly(score=0.05):
    return AnomalyResult(score=score, baseline_ready=True, z_scores={}, feature_values={})


def test_healthy_sample_scores_high():
    result = HealthEngine().evaluate(raw(), anomaly())
    assert result.score >= 80
    assert result.state == "HEALTHY"


def test_bad_vibration_and_temperature_go_critical():
    result = HealthEngine().evaluate(
        raw(vibration=5.0, bearing=86, motor=102, current=13),
        anomaly(0.95),
    )
    assert result.score < 60
    assert result.state == "CRITICAL"
    assert result.contributors
