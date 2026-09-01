from __future__ import annotations

from typing import Any

from asyncua import Client, ua

from common.node_ids import CONTROL_NODE_IDS
from common.settings import settings


class OpcUaControlClient:
    def __init__(self, url: str = settings.opcua_url) -> None:
        self.url = url

    async def _nodes(self, client: Client) -> dict[str, Any]:
        ns = await client.get_namespace_index(settings.namespace_uri)
        return {
            name: client.get_node(f"ns={ns};s={identifier}")
            for name, identifier in CONTROL_NODE_IDS.items()
        }

    async def read_state(self) -> dict[str, Any]:
        async with Client(url=self.url) as client:
            nodes = await self._nodes(client)
            return {
                "fault_mode": str(await nodes["fault_mode"].read_value()),
                "fault_intensity": float(await nodes["fault_intensity"].read_value()),
                "target_load": float(await nodes["target_load"].read_value()),
                "running_command": bool(await nodes["running_command"].read_value()),
                "reset_fault": bool(await nodes["reset_fault"].read_value()),
            }

    async def set_fault(self, mode: str, intensity: float) -> dict[str, Any]:
        async with Client(url=self.url) as client:
            nodes = await self._nodes(client)
            await nodes["fault_mode"].write_value(
                ua.Variant(mode, ua.VariantType.String)
            )
            await nodes["fault_intensity"].write_value(
                ua.Variant(float(intensity), ua.VariantType.Double)
            )
        return await self.read_state()

    async def reset(self) -> dict[str, Any]:
        async with Client(url=self.url) as client:
            nodes = await self._nodes(client)
            await nodes["fault_mode"].write_value(
                ua.Variant("NONE", ua.VariantType.String)
            )
            await nodes["fault_intensity"].write_value(
                ua.Variant(0.0, ua.VariantType.Double)
            )
            await nodes["reset_fault"].write_value(
                ua.Variant(True, ua.VariantType.Boolean)
            )
        return await self.read_state()

    async def set_target_load(self, target_load: float) -> dict[str, Any]:
        async with Client(url=self.url) as client:
            nodes = await self._nodes(client)
            await nodes["target_load"].write_value(
                ua.Variant(float(target_load), ua.VariantType.Double)
            )
        return await self.read_state()

    async def set_running(self, running: bool) -> dict[str, Any]:
        async with Client(url=self.url) as client:
            nodes = await self._nodes(client)
            await nodes["running_command"].write_value(
                ua.Variant(bool(running), ua.VariantType.Boolean)
            )
        return await self.read_state()
