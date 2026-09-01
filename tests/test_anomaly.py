from datetime import datetime, timezone

from analytics.anomaly import AnomalyEngine
from common.models import RawTelemetry


def sample(vibration=1.1, bearing=48.0, motor=64.0, current=8.7, load=60.0):
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
        operating_hours=1200,
    )


def test_anomaly_baseline_and_fault_deviation():
    engine = AnomalyEngine(baseline_samples=10)
    for i in range(10):
        result = engine.evaluate(sample(vibration=1.08 + i * 0.002, bearing=49 + i * 0.03))
    assert result.baseline_ready

    abnormal = engine.evaluate(sample(vibration=4.2, bearing=78, motor=88, current=11.5))
    assert abnormal.score > 0.7
    assert abnormal.z_scores["vibration_residual"] > 3


def test_anomaly_state_round_trip():
    engine = AnomalyEngine(baseline_samples=10)
    for _ in range(10):
        engine.evaluate(sample())
    saved = engine.to_state()

    restored = AnomalyEngine(baseline_samples=10)
    restored.load_state(saved)
    assert restored.baseline_ready
    assert restored.evaluate(sample()).score < 0.2
