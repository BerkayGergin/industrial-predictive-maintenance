from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=4) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    print("Waiting for API and telemetry...")
    deadline = time.time() + 60
    last_error = None
    while time.time() < deadline:
        try:
            health = get("/api/health")
            current = get("/api/motors/Motor_01/current")
            print("API:", health["status"])
            print(
                "Motor:",
                current["health_state"],
                f"health={current['health_score']}",
                f"vibration={current['vibration']}",
                f"anomaly={current['anomaly_score']}",
            )
            print("Smoke check passed.")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise SystemExit(f"Smoke check failed: {last_error}")


if __name__ == "__main__":
    main()
