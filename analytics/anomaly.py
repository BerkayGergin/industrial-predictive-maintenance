from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any

from common.models import AnomalyResult, RawTelemetry


class AnomalyEngine:
    """Explainable residual detector with a frozen healthy baseline.

    The electrical/mechanical residuals are compensated for load directly.
    Temperatures use a small nominal first-order thermal predictor so normal
    heating/cooling lag is not mistaken for a fault. The first N residual
    snapshots form a baseline; after that, the baseline is frozen and persisted.

    The simulator's injected fault label is deliberately NOT used in scoring.
    """

    FEATURE_FLOORS = {
        "vibration_residual": 0.08,
        "bearing_temp_residual": 0.35,
        "motor_temp_residual": 0.45,
        "current_residual": 0.20,
    }

    def __init__(self, baseline_samples: int = 30) -> None:
        self.baseline_samples = max(10, int(baseline_samples))
        self._warmup: dict[str, list[float]] = defaultdict(list)
        self._stats: dict[str, tuple[float, float]] = {}
        self._expected_motor_temp: float | None = None
        self._expected_bearing_temp: float | None = None
        self._last_time: datetime | None = None

    @property
    def baseline_ready(self) -> bool:
        return bool(self._stats)

    def _thermal_predictions(self, sample: RawTelemetry) -> tuple[float, float]:
        load_fraction = max(0.0, min(1.0, sample.load / 100.0))
        if not sample.running:
            motor_target = sample.ambient_temperature + 2.0
            bearing_target = sample.ambient_temperature + 1.0
        else:
            motor_target = sample.ambient_temperature + 18.0 + 42.0 * load_fraction
            bearing_target = sample.ambient_temperature + 10.0 + 24.0 * load_fraction

        if self._expected_motor_temp is None:
            self._expected_motor_temp = sample.motor_temperature
        if self._expected_bearing_temp is None:
            self._expected_bearing_temp = sample.bearing_temperature

        if self._last_time is None:
            dt = 1.0
        else:
            dt = (sample.time - self._last_time).total_seconds()
            dt = max(0.1, min(5.0, dt))
        self._last_time = sample.time

        motor_alpha = 1.0 - math.exp(-dt / 22.0)
        bearing_alpha = 1.0 - math.exp(-dt / 16.0)
        self._expected_motor_temp += (motor_target - self._expected_motor_temp) * motor_alpha
        self._expected_bearing_temp += (bearing_target - self._expected_bearing_temp) * bearing_alpha
        return self._expected_motor_temp, self._expected_bearing_temp

    def _features(self, sample: RawTelemetry) -> dict[str, float]:
        load_fraction = max(0.0, min(1.0, sample.load / 100.0))
        expected_vibration = 0.62 + 0.78 * load_fraction if sample.running else 0.05
        expected_current = 2.2 + 10.8 * load_fraction if sample.running else 0.04
        expected_motor_temp, expected_bearing_temp = self._thermal_predictions(sample)

        return {
            "vibration_residual": sample.vibration - expected_vibration,
            "bearing_temp_residual": sample.bearing_temperature - expected_bearing_temp,
            "motor_temp_residual": sample.motor_temperature - expected_motor_temp,
            "current_residual": sample.current - expected_current,
        }

    def _finish_baseline_if_ready(self) -> None:
        if self.baseline_ready or not self._warmup:
            return
        if min(len(values) for values in self._warmup.values()) < self.baseline_samples:
            return

        stats: dict[str, tuple[float, float]] = {}
        for name, values in self._warmup.items():
            selected = values[: self.baseline_samples]
            mean = statistics.fmean(selected)
            stdev = statistics.stdev(selected) if len(selected) >= 2 else 0.0
            stdev = max(stdev, self.FEATURE_FLOORS[name])
            stats[name] = (mean, stdev)
        self._stats = stats

    def evaluate(self, sample: RawTelemetry) -> AnomalyResult:
        features = self._features(sample)

        if not self.baseline_ready:
            for name, value in features.items():
                self._warmup[name].append(float(value))
            self._finish_baseline_if_ready()

        if not self.baseline_ready:
            return AnomalyResult(
                score=0.0,
                baseline_ready=False,
                z_scores={name: 0.0 for name in features},
                feature_values={name: round(value, 4) for name, value in features.items()},
            )

        z_scores: dict[str, float] = {}
        for name, value in features.items():
            mean, stdev = self._stats[name]
            z_scores[name] = abs(value - mean) / stdev

        ordered = sorted(z_scores.values(), reverse=True)
        max_z = ordered[0] if ordered else 0.0
        second_z = ordered[1] if len(ordered) > 1 else 0.0
        combined_z = 0.75 * max_z + 0.25 * second_z

        # Below ~2 sigma the sample is treated as normal. The exponential tail
        # makes the score rise smoothly instead of jumping at one threshold.
        score = 0.0 if combined_z <= 2.0 else 1.0 - math.exp(-(combined_z - 2.0) / 3.0)
        score = max(0.0, min(1.0, score))

        return AnomalyResult(
            score=round(score, 4),
            baseline_ready=True,
            z_scores={name: round(value, 3) for name, value in z_scores.items()},
            feature_values={name: round(value, 4) for name, value in features.items()},
        )

    def to_state(self) -> dict[str, Any]:
        return {
            "baseline_samples": self.baseline_samples,
            "warmup": dict(self._warmup),
            "stats": {
                name: {"mean": mean, "stdev": stdev}
                for name, (mean, stdev) in self._stats.items()
            },
            "predictor": {
                "expected_motor_temp": self._expected_motor_temp,
                "expected_bearing_temp": self._expected_bearing_temp,
                "last_time": self._last_time.isoformat() if self._last_time else None,
            },
        }

    def load_state(self, state: dict[str, Any] | None) -> None:
        if not state:
            return
        warmup = state.get("warmup") or {}
        stats = state.get("stats") or {}
        predictor = state.get("predictor") or {}
        self._warmup = defaultdict(
            list,
            {name: [float(v) for v in values] for name, values in warmup.items()},
        )
        self._stats = {
            name: (float(data["mean"]), float(data["stdev"]))
            for name, data in stats.items()
            if "mean" in data and "stdev" in data
        }
        if predictor.get("expected_motor_temp") is not None:
            self._expected_motor_temp = float(predictor["expected_motor_temp"])
        if predictor.get("expected_bearing_temp") is not None:
            self._expected_bearing_temp = float(predictor["expected_bearing_temp"])
        if predictor.get("last_time"):
            self._last_time = datetime.fromisoformat(str(predictor["last_time"]))
