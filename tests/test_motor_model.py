from simulator.motor_model import MotorModel


def run(model: MotorModel, seconds: float, **kwargs):
    snap = None
    dt = 0.25
    for _ in range(int(seconds / dt)):
        snap = model.step(dt, **kwargs)
    return snap


def test_bearing_wear_increases_vibration_and_temperature():
    normal = MotorModel(seed=7)
    normal_snap = run(normal, 80, fault_mode="NONE", target_load=60)

    faulty = MotorModel(seed=7)
    fault_snap = run(
        faulty,
        80,
        fault_mode="BEARING_WEAR",
        fault_intensity=1.0,
        target_load=60,
    )

    assert fault_snap.vibration > normal_snap.vibration + 1.5
    assert fault_snap.bearing_temperature > normal_snap.bearing_temperature + 8


def test_overload_pushes_load_and_current():
    model = MotorModel(seed=3)
    snap = run(
        model,
        50,
        fault_mode="OVERLOAD",
        fault_intensity=1.0,
        target_load=30,
    )
    assert snap.load > 80
    assert snap.current > 10


def test_stopped_motor_has_zero_rpm():
    model = MotorModel(seed=2)
    snap = run(model, 5, running_command=False)
    assert snap.running is False
    assert snap.rpm == 0.0
    assert snap.power == 0.0
