from __future__ import annotations

from common.models import AnomalyResult, HealthResult, RawTelemetry


def _linear_penalty(value: float, warning: float, critical: float, max_penalty: float) -> float:
    if value <= warning:
        return 0.0
    if critical <= warning:
        return max_penalty
    ratio = min(1.0, (value - warning) / (critical - warning))
    return ratio * max_penalty


class HealthEngine:
    def evaluate(self, sample: RawTelemetry, anomaly: AnomalyResult) -> HealthResult:
        contributors: list[dict[str, float | str]] = []

        def add(name: str, value: float, unit: str, penalty: float) -> None:
            if penalty <= 0.01:
                return
            contributors.append(
                {
                    "name": name,
                    "value": round(value, 3),
                    "unit": unit,
                    "penalty": round(penalty, 1),
                }
            )

        vibration_penalty = _linear_penalty(sample.vibration, 1.8, 4.5, 34.0)
        bearing_penalty = _linear_penalty(sample.bearing_temperature, 58.0, 82.0, 25.0)
        motor_temp_penalty = _linear_penalty(sample.motor_temperature, 72.0, 100.0, 20.0)

        load_fraction = max(sample.load / 100.0, 0.05)
        expected_current = 2.2 + 10.8 * load_fraction if sample.running else 0.04
        current_ratio = sample.current / max(expected_current, 0.1)
        current_penalty = _linear_penalty(current_ratio, 1.12, 1.45, 12.0)
        anomaly_penalty = anomaly.score * 24.0 if anomaly.baseline_ready else 0.0

        add("Vibration", sample.vibration, "mm/s", vibration_penalty)
        add("Bearing temperature", sample.bearing_temperature, "°C", bearing_penalty)
        add("Motor temperature", sample.motor_temperature, "°C", motor_temp_penalty)
        add("Current vs expected", current_ratio, "ratio", current_penalty)
        add("Statistical anomaly", anomaly.score, "score", anomaly_penalty)

        total_penalty = sum(float(item["penalty"]) for item in contributors)
        score = int(round(max(0.0, min(100.0, 100.0 - total_penalty))))

        hard_critical = (
            sample.vibration >= 4.5
            or sample.bearing_temperature >= 82.0
            or sample.motor_temperature >= 100.0
        )
        if hard_critical or score < 60:
            state = "CRITICAL"
        elif score < 80:
            state = "WARNING"
        else:
            state = "HEALTHY"

        contributors.sort(key=lambda item: float(item["penalty"]), reverse=True)
        top = contributors[0]["name"] if contributors else "None"
        recommendation = self._recommend(top, state, anomaly.baseline_ready)

        return HealthResult(
            score=score,
            state=state,
            contributors=contributors,
            recommendation=recommendation,
        )

    @staticmethod
    def _recommend(top_contributor: str, state: str, baseline_ready: bool) -> str:
        if not baseline_ready:
            return "Collecting healthy baseline; avoid interpreting anomaly score yet."
        if state == "HEALTHY":
            return "No maintenance action indicated; continue condition monitoring."
        if top_contributor == "Vibration":
            return "Inspect bearing condition, alignment and mounting before continued high-load operation."
        if top_contributor == "Bearing temperature":
            return "Inspect bearing lubrication, friction and bearing housing temperature."
        if top_contributor == "Motor temperature":
            return "Inspect cooling path, airflow and sustained motor loading."
        if top_contributor == "Current vs expected":
            return "Inspect mechanical load and electrical current draw against the operating point."
        return "Review recent trends and investigate the strongest abnormal sensor residuals."
