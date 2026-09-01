from __future__ import annotations

import json
from typing import Any, Iterable

import asyncpg

from analytics.alarms import AlarmCondition
from common.models import AnalyzedTelemetry


_SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}


def _decode_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _record_to_dict(record: asyncpg.Record | None) -> dict[str, Any] | None:
    if record is None:
        return None
    data = dict(record)
    if "analysis" in data:
        data["analysis"] = _decode_json(data["analysis"])
    if "state" in data and isinstance(data.get("state"), str) and data.get("motor_id") and "updated_at" in data:
        data["state"] = _decode_json(data["state"])
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=1,
                max_size=8,
                command_timeout=10,
            )

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not connected")
        return self.pool

    async def ping(self) -> bool:
        try:
            return bool(await self._require_pool().fetchval("SELECT 1"))
        except Exception:
            return False

    async def insert_telemetry(self, sample: AnalyzedTelemetry) -> None:
        raw = sample.raw
        analysis = {
            "z_scores": sample.anomaly.z_scores,
            "feature_values": sample.anomaly.feature_values,
            "contributors": sample.health.contributors,
            "recommendation": sample.health.recommendation,
        }
        await self._require_pool().execute(
            """
            INSERT INTO telemetry (
                time, motor_id, voltage, current, power, rpm, load, vibration,
                motor_temperature, bearing_temperature, ambient_temperature,
                running, operating_hours, fault_mode, fault_progress,
                anomaly_score, anomaly_baseline_ready, health_score,
                health_state, analysis
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20::jsonb
            )
            """,
            raw.time,
            raw.motor_id,
            raw.voltage,
            raw.current,
            raw.power,
            raw.rpm,
            raw.load,
            raw.vibration,
            raw.motor_temperature,
            raw.bearing_temperature,
            raw.ambient_temperature,
            raw.running,
            raw.operating_hours,
            raw.fault_mode,
            raw.fault_progress,
            sample.anomaly.score,
            sample.anomaly.baseline_ready,
            sample.health.score,
            sample.health.state,
            json.dumps(analysis),
        )

    async def latest_telemetry(self, motor_id: str) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            """
            SELECT * FROM telemetry
            WHERE motor_id = $1
            ORDER BY time DESC
            LIMIT 1
            """,
            motor_id,
        )
        return _record_to_dict(row)

    async def history(
        self,
        motor_id: str,
        minutes: int = 60,
        limit: int = 1800,
    ) -> list[dict[str, Any]]:
        minutes = max(1, min(int(minutes), 24 * 60))
        limit = max(10, min(int(limit), 5000))
        rows = await self._require_pool().fetch(
            """
            SELECT
                time, motor_id, rpm, load, current, power, vibration,
                motor_temperature, bearing_temperature, health_score,
                health_state, anomaly_score, anomaly_baseline_ready,
                fault_mode, fault_progress
            FROM telemetry
            WHERE motor_id = $1
              AND time >= NOW() - ($2::int * INTERVAL '1 minute')
            ORDER BY time ASC
            LIMIT $3
            """,
            motor_id,
            minutes,
            limit,
        )
        return [_record_to_dict(row) or {} for row in rows]

    async def list_motors(self) -> list[dict[str, Any]]:
        rows = await self._require_pool().fetch(
            """
            SELECT DISTINCT ON (motor_id)
                motor_id, time, health_score, health_state, rpm, load,
                vibration, bearing_temperature, anomaly_score
            FROM telemetry
            ORDER BY motor_id, time DESC
            """
        )
        return [_record_to_dict(row) or {} for row in rows]

    async def list_alarms(
        self,
        motor_id: str | None = None,
        open_only: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if motor_id:
            args.append(motor_id)
            clauses.append(f"motor_id = ${len(args)}")
        if open_only:
            clauses.append("state <> 'CLEARED'")
        args.append(max(1, min(int(limit), 1000)))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = f"""
            SELECT * FROM alarms
            {where}
            ORDER BY
                CASE state WHEN 'ACTIVE' THEN 0 WHEN 'ACKNOWLEDGED' THEN 1 ELSE 2 END,
                activated_at DESC
            LIMIT ${len(args)}
        """
        rows = await self._require_pool().fetch(query, *args)
        return [_record_to_dict(row) or {} for row in rows]

    async def get_alarm(self, alarm_id: int) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            "SELECT * FROM alarms WHERE id = $1", alarm_id
        )
        return _record_to_dict(row)

    async def acknowledge_alarm(self, alarm_id: int, acknowledged_by: str) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            """
            UPDATE alarms
            SET state = 'ACKNOWLEDGED',
                acknowledged_at = NOW(),
                acknowledged_by = $2
            WHERE id = $1 AND state = 'ACTIVE'
            RETURNING *
            """,
            alarm_id,
            acknowledged_by[:80],
        )
        if row is not None:
            return _record_to_dict(row)
        return await self.get_alarm(alarm_id)

    async def reconcile_alarm_conditions(
        self,
        motor_id: str,
        conditions: Iterable[AlarmCondition],
    ) -> None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for condition in conditions:
                    existing = await conn.fetchrow(
                        """
                        SELECT * FROM alarms
                        WHERE motor_id = $1 AND code = $2 AND state <> 'CLEARED'
                        LIMIT 1
                        FOR UPDATE
                        """,
                        motor_id,
                        condition.code,
                    )

                    if condition.active and existing is None:
                        await conn.execute(
                            """
                            INSERT INTO alarms (
                                motor_id, code, severity, message, state,
                                value, threshold, unit, activated_at, last_seen_at
                            ) VALUES ($1,$2,$3,$4,'ACTIVE',$5,$6,$7,NOW(),NOW())
                            """,
                            motor_id,
                            condition.code,
                            condition.severity,
                            condition.message,
                            condition.value,
                            condition.threshold,
                            condition.unit,
                        )
                        continue

                    if condition.active and existing is not None:
                        escalated = _SEVERITY_RANK[condition.severity] > _SEVERITY_RANK[str(existing["severity"])]
                        if escalated and existing["state"] == "ACKNOWLEDGED":
                            await conn.execute(
                                """
                                UPDATE alarms
                                SET severity=$3, message=$4, value=$5, threshold=$6, unit=$7,
                                    state='ACTIVE', acknowledged_at=NULL, acknowledged_by=NULL,
                                    last_seen_at=NOW()
                                WHERE id=$1 AND motor_id=$2
                                """,
                                existing["id"],
                                motor_id,
                                condition.severity,
                                condition.message,
                                condition.value,
                                condition.threshold,
                                condition.unit,
                            )
                        else:
                            await conn.execute(
                                """
                                UPDATE alarms
                                SET severity=$3, message=$4, value=$5, threshold=$6, unit=$7,
                                    last_seen_at=NOW()
                                WHERE id=$1 AND motor_id=$2
                                """,
                                existing["id"],
                                motor_id,
                                condition.severity,
                                condition.message,
                                condition.value,
                                condition.threshold,
                                condition.unit,
                            )
                        continue

                    if not condition.active and existing is not None:
                        await conn.execute(
                            """
                            UPDATE alarms
                            SET state='CLEARED', cleared_at=NOW(), last_seen_at=NOW(),
                                value=$3, threshold=$4, unit=$5
                            WHERE id=$1 AND motor_id=$2
                            """,
                            existing["id"],
                            motor_id,
                            condition.value,
                            condition.threshold,
                            condition.unit,
                        )

    async def load_analytics_state(self, motor_id: str) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            "SELECT state FROM analytics_state WHERE motor_id = $1", motor_id
        )
        if row is None:
            return None
        return _decode_json(row["state"])

    async def save_analytics_state(self, motor_id: str, state: dict[str, Any]) -> None:
        await self._require_pool().execute(
            """
            INSERT INTO analytics_state (motor_id, state, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (motor_id)
            DO UPDATE SET state=EXCLUDED.state, updated_at=NOW()
            """,
            motor_id,
            json.dumps(state),
        )
