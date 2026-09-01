from __future__ import annotations

import math
import random
from dataclasses import dataclass

from common.node_ids import FAULT_MODES


@dataclass(slots=True)
class MotorSnapshot:
    voltage: float
    current: float
    power: float
    rpm: float
    load: float
    vibration: float
    motor_temperature: float
    bearing_temperature: float
    ambient_temperature: float
    running: bool
    operating_hours: float
    fault_mode: str
    fault_progress: float


class MotorModel:
    """Small deterministic motor digital twin for a condition-monitoring lab.

    The model is intentionally understandable rather than physically exhaustive.
    Values are coupled: load drives current/power/temperature, while injected
    faults alter vibration, temperature and load behaviour gradually.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.elapsed = 0.0
        self.operating_hours = 1250.0
        self.running = True
        self.load = 45.0
        self.motor_temperature = 61.0
        self.bearing_temperature = 46.0
        self.ambient_temperature = 25.0
        self.fault_progress = 0.0
        self._last_fault_mode = "NONE"

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def reset_fault_state(self) -> None:
        self.fault_progress = 0.0
        self._last_fault_mode = "NONE"

    def _fault_target(self, mode: str, intensity: float) -> float:
        if mode == "NONE":
            return 0.0
        return self._clamp(intensity, 0.0, 1.0)

    def _update_fault_progress(self, dt: float, mode: str, intensity: float) -> None:
        target = self._fault_target(mode, intensity)
        # Faults build over ~25 s at full intensity and recover over ~35 s.
        time_constant = 25.0 if target > self.fault_progress else 35.0
        alpha = 1.0 - math.exp(-dt / time_constant)
        self.fault_progress += (target - self.fault_progress) * alpha
        if mode == "NONE" and self.fault_progress < 0.001:
            self.fault_progress = 0.0
        self._last_fault_mode = mode

    def step(
        self,
        dt: float,
        *,
        fault_mode: str = "NONE",
        fault_intensity: float = 1.0,
        target_load: float = -1.0,
        running_command: bool = True,
        reset_fault: bool = False,
    ) -> MotorSnapshot:
        if fault_mode not in FAULT_MODES:
            fault_mode = "NONE"
        if reset_fault:
            self.reset_fault_state()
            fault_mode = "NONE"
            fault_intensity = 0.0

        self.elapsed += dt
        self.running = bool(running_command)
        self._update_fault_progress(dt, fault_mode, fault_intensity)
        p = self.fault_progress

        if not self.running:
            desired_load = 0.0
        elif 0.0 <= target_load <= 100.0:
            desired_load = target_load
        else:
            # Slow production-cycle profile with a small secondary oscillation.
            desired_load = (
                52.0
                + 24.0 * math.sin(self.elapsed / 28.0)
                + 7.0 * math.sin(self.elapsed / 9.0)
            )

        if fault_mode == "OVERLOAD":
            desired_load = max(desired_load, 82.0 + 18.0 * p)

        desired_load = self._clamp(desired_load, 0.0, 100.0)
        load_alpha = 1.0 - math.exp(-dt / 2.5)
        self.load += (desired_load - self.load) * load_alpha
        load_fraction = self.load / 100.0

        if self.running:
            voltage = 400.0 + self.rng.gauss(0.0, 0.8)
            current = 2.2 + 10.8 * load_fraction
            current += self.rng.gauss(0.0, 0.07)
            if fault_mode == "MISALIGNMENT":
                current += 0.8 * p
            if fault_mode == "OVERLOAD":
                current += 1.4 * p

            # Three-phase active power approximation.
            power_factor = 0.78 + 0.10 * load_fraction
            efficiency = 0.90
            power = math.sqrt(3.0) * voltage * current * power_factor * efficiency / 1000.0

            slip = 0.012 + 0.020 * load_fraction
            rpm = 1500.0 * (1.0 - slip)
            if fault_mode == "MISALIGNMENT":
                rpm -= 12.0 * p
            rpm += self.rng.gauss(0.0, 1.5)
        else:
            voltage = 400.0 + self.rng.gauss(0.0, 0.5)
            current = max(0.0, self.rng.gauss(0.04, 0.01))
            power = 0.0
            rpm = 0.0

        vibration = 0.62 + 0.78 * load_fraction if self.running else 0.05
        if fault_mode == "BEARING_WEAR":
            vibration += 3.6 * p
        elif fault_mode == "MISALIGNMENT":
            vibration += 2.8 * p
        elif fault_mode == "OVERLOAD":
            vibration += 0.7 * p
        vibration += self.rng.gauss(0.0, 0.035)
        vibration = max(0.02, vibration)

        # Thermal model: first-order response to heat generation and cooling.
        normal_motor_target = self.ambient_temperature + 18.0 + 42.0 * load_fraction
        normal_bearing_target = self.ambient_temperature + 10.0 + 24.0 * load_fraction

        if fault_mode == "COOLING_FAILURE":
            normal_motor_target += 36.0 * p
            normal_bearing_target += 18.0 * p
        if fault_mode == "BEARING_WEAR":
            normal_bearing_target += 30.0 * p
            normal_motor_target += 6.0 * p
        if fault_mode == "MISALIGNMENT":
            normal_bearing_target += 14.0 * p
            normal_motor_target += 8.0 * p
        if fault_mode == "OVERLOAD":
            normal_motor_target += 18.0 * p
            normal_bearing_target += 9.0 * p

        if not self.running:
            normal_motor_target = self.ambient_temperature + 2.0
            normal_bearing_target = self.ambient_temperature + 1.0

        motor_tau = 22.0
        bearing_tau = 16.0
        self.motor_temperature += (
            normal_motor_target - self.motor_temperature
        ) * (1.0 - math.exp(-dt / motor_tau))
        self.bearing_temperature += (
            normal_bearing_target - self.bearing_temperature
        ) * (1.0 - math.exp(-dt / bearing_tau))

        self.motor_temperature += self.rng.gauss(0.0, 0.03)
        self.bearing_temperature += self.rng.gauss(0.0, 0.025)

        if self.running:
            self.operating_hours += dt / 3600.0

        return MotorSnapshot(
            voltage=round(voltage, 2),
            current=round(current, 3),
            power=round(power, 3),
            rpm=round(rpm, 2),
            load=round(self.load, 2),
            vibration=round(vibration, 4),
            motor_temperature=round(self.motor_temperature, 2),
            bearing_temperature=round(self.bearing_temperature, 2),
            ambient_temperature=round(self.ambient_temperature, 2),
            running=self.running,
            operating_hours=round(self.operating_hours, 5),
            fault_mode=fault_mode,
            fault_progress=round(self.fault_progress, 4),
        )
