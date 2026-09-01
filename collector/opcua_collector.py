from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from asyncua import Client

from analytics.alarms import evaluate_alarm_conditions
from analytics.anomaly import AnomalyEngine
from analytics.health import HealthEngine
from common.db import Database
from common.models import AnalyzedTelemetry, RawTelemetry
from common.node_ids import SENSOR_NODE_IDS
from common.settings import settings

logger = logging.getLogger("collector.opcua")
NODE_TO_FIELD = {identifier: field for field, identifier in SENSOR_NODE_IDS.items()}
REQUIRED_FIELDS = set(SENSOR_NODE_IDS)


class SubscriptionHandler:
    def __init__(self) -> None:
        self.latest: dict[str, Any] = {}
        self.last_update_monotonic = 0.0

    def datachange_notification(self, node, value, data) -> None:  # asyncua callback signature
        identifier = str(node.nodeid.Identifier)
        field = NODE_TO_FIELD.get(identifier)
        if field is None:
            return
        self.latest[field] = value
        self.last_update_monotonic = time.monotonic()


class CollectorService:
    def __init__(self) -> None:
        self.db = Database(settings.database_url)
        self.anomaly = AnomalyEngine(settings.baseline_samples)
        self.health = HealthEngine()
        self.sample_count = 0

    async def start(self) -> None:
        await self.db.connect()
        saved_state = await self.db.load_analytics_state(settings.motor_id)
        if saved_state:
            self.anomaly.load_state(saved_state)
            logger.info("Loaded persisted anomaly baseline state")

        retry_seconds = 2.0
        while True:
            try:
                await self._run_connected()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Collector connection failed: %s", exc)
                await asyncio.sleep(retry_seconds)

    async def _run_connected(self) -> None:
        handler = SubscriptionHandler()
        logger.info("Connecting to OPC UA server: %s", settings.opcua_url)

        async with Client(url=settings.opcua_url) as client:
            namespace_index = await client.get_namespace_index(settings.namespace_uri)
            logger.info("OPC UA connected; namespace index=%s", namespace_index)

            nodes = {
                field: client.get_node(f"ns={namespace_index};s={identifier}")
                for field, identifier in SENSOR_NODE_IDS.items()
            }

            # Seed a coherent initial state before subscription notifications arrive.
            for field, node in nodes.items():
                handler.latest[field] = await node.read_value()
            handler.last_update_monotonic = time.monotonic()

            subscription = await client.create_subscription(
                settings.collector_publish_ms,
                handler,
            )
            await subscription.subscribe_data_change(
                list(nodes.values()),
                sampling_interval=settings.collector_sampling_ms,
                queuesize=10,
            )
            logger.info(
                "Subscribed to %d monitored items (sampling=%d ms, publishing=%d ms)",
                len(nodes),
                settings.collector_sampling_ms,
                settings.collector_publish_ms,
            )

            while True:
                await asyncio.sleep(settings.collector_snapshot_seconds)
                age = time.monotonic() - handler.last_update_monotonic
                if age > max(4.0, settings.collector_snapshot_seconds * 4):
                    raise ConnectionError(f"OPC UA subscription stale for {age:.1f}s")

                if not REQUIRED_FIELDS.issubset(handler.latest):
                    missing = sorted(REQUIRED_FIELDS - set(handler.latest))
                    logger.warning("Waiting for OPC UA values; missing=%s", missing)
                    continue

                await self._process_snapshot(dict(handler.latest))

    async def _process_snapshot(self, values: dict[str, Any]) -> None:
        raw = RawTelemetry(
            motor_id=settings.motor_id,
            time=datetime.now(timezone.utc),
            voltage=float(values["voltage"]),
            current=float(values["current"]),
            power=float(values["power"]),
            rpm=float(values["rpm"]),
            load=float(values["load"]),
            vibration=float(values["vibration"]),
            motor_temperature=float(values["motor_temperature"]),
            bearing_temperature=float(values["bearing_temperature"]),
            ambient_temperature=float(values["ambient_temperature"]),
            running=bool(values["running"]),
            operating_hours=float(values["operating_hours"]),
            fault_mode=str(values["fault_mode"]),
            fault_progress=float(values["fault_progress"]),
        )

        anomaly = self.anomaly.evaluate(raw)
        health = self.health.evaluate(raw, anomaly)
        analyzed = AnalyzedTelemetry(raw=raw, anomaly=anomaly, health=health)

        await self.db.insert_telemetry(analyzed)
        await self.db.reconcile_alarm_conditions(
            settings.motor_id,
            evaluate_alarm_conditions(analyzed),
        )

        self.sample_count += 1
        if self.sample_count % 10 == 0 or (anomaly.baseline_ready and self.sample_count % 5 == 0):
            await self.db.save_analytics_state(settings.motor_id, self.anomaly.to_state())

        if self.sample_count % 10 == 0:
            logger.info(
                "telemetry health=%s/%s anomaly=%.2f load=%.1f%% vib=%.2fmm/s bearing=%.1fC fault=%s %.0f%%",
                health.state,
                health.score,
                anomaly.score,
                raw.load,
                raw.vibration,
                raw.bearing_temperature,
                raw.fault_mode,
                raw.fault_progress * 100,
            )


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    service = CollectorService()
    try:
        await service.start()
    finally:
        await service.db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
