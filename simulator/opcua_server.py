from __future__ import annotations

import asyncio
import logging

from asyncua import Server, ua

from common.node_ids import CONTROL_NODE_IDS, SENSOR_NODE_IDS
from common.settings import settings
from simulator.motor_model import MotorModel

logger = logging.getLogger("simulator.opcua")


async def _add_variable(parent, namespace_index: int, identifier: str, browse_name: str, value, variant_type):
    node = await parent.add_variable(
        ua.NodeId(identifier, namespace_index),
        browse_name,
        value,
        varianttype=variant_type,
    )
    return node


async def build_address_space(server: Server, namespace_index: int):
    objects = server.nodes.objects
    factory = await objects.add_object(ua.NodeId("Factory", namespace_index), "Factory")
    motor = await factory.add_object(
        ua.NodeId(settings.motor_id, namespace_index), settings.motor_id
    )

    electrical = await motor.add_object(
        ua.NodeId(f"{settings.motor_id}.Electrical", namespace_index), "Electrical"
    )
    mechanical = await motor.add_object(
        ua.NodeId(f"{settings.motor_id}.Mechanical", namespace_index), "Mechanical"
    )
    thermal = await motor.add_object(
        ua.NodeId(f"{settings.motor_id}.Thermal", namespace_index), "Thermal"
    )
    status = await motor.add_object(
        ua.NodeId(f"{settings.motor_id}.Status", namespace_index), "Status"
    )
    controls = await motor.add_object(
        ua.NodeId(f"{settings.motor_id}.Controls", namespace_index), "Controls"
    )

    nodes = {}
    nodes["voltage"] = await _add_variable(electrical, namespace_index, SENSOR_NODE_IDS["voltage"], "Voltage", 400.0, ua.VariantType.Double)
    nodes["current"] = await _add_variable(electrical, namespace_index, SENSOR_NODE_IDS["current"], "Current", 0.0, ua.VariantType.Double)
    nodes["power"] = await _add_variable(electrical, namespace_index, SENSOR_NODE_IDS["power"], "Power", 0.0, ua.VariantType.Double)

    nodes["rpm"] = await _add_variable(mechanical, namespace_index, SENSOR_NODE_IDS["rpm"], "RPM", 0.0, ua.VariantType.Double)
    nodes["load"] = await _add_variable(mechanical, namespace_index, SENSOR_NODE_IDS["load"], "Load", 0.0, ua.VariantType.Double)
    nodes["vibration"] = await _add_variable(mechanical, namespace_index, SENSOR_NODE_IDS["vibration"], "Vibration", 0.0, ua.VariantType.Double)

    nodes["motor_temperature"] = await _add_variable(thermal, namespace_index, SENSOR_NODE_IDS["motor_temperature"], "MotorTemperature", 45.0, ua.VariantType.Double)
    nodes["bearing_temperature"] = await _add_variable(thermal, namespace_index, SENSOR_NODE_IDS["bearing_temperature"], "BearingTemperature", 40.0, ua.VariantType.Double)
    nodes["ambient_temperature"] = await _add_variable(thermal, namespace_index, SENSOR_NODE_IDS["ambient_temperature"], "AmbientTemperature", 25.0, ua.VariantType.Double)

    nodes["running"] = await _add_variable(status, namespace_index, SENSOR_NODE_IDS["running"], "Running", True, ua.VariantType.Boolean)
    nodes["operating_hours"] = await _add_variable(status, namespace_index, SENSOR_NODE_IDS["operating_hours"], "OperatingHours", 1250.0, ua.VariantType.Double)
    nodes["fault_mode"] = await _add_variable(status, namespace_index, SENSOR_NODE_IDS["fault_mode"], "FaultMode", "NONE", ua.VariantType.String)
    nodes["fault_progress"] = await _add_variable(status, namespace_index, SENSOR_NODE_IDS["fault_progress"], "FaultProgress", 0.0, ua.VariantType.Double)

    control_nodes = {}
    control_nodes["fault_mode"] = await _add_variable(controls, namespace_index, CONTROL_NODE_IDS["fault_mode"], "FaultMode", "NONE", ua.VariantType.String)
    control_nodes["fault_intensity"] = await _add_variable(controls, namespace_index, CONTROL_NODE_IDS["fault_intensity"], "FaultIntensity", 1.0, ua.VariantType.Double)
    control_nodes["target_load"] = await _add_variable(controls, namespace_index, CONTROL_NODE_IDS["target_load"], "TargetLoad", -1.0, ua.VariantType.Double)
    control_nodes["running_command"] = await _add_variable(controls, namespace_index, CONTROL_NODE_IDS["running_command"], "RunningCommand", True, ua.VariantType.Boolean)
    control_nodes["reset_fault"] = await _add_variable(controls, namespace_index, CONTROL_NODE_IDS["reset_fault"], "ResetFault", False, ua.VariantType.Boolean)

    for node in control_nodes.values():
        await node.set_writable()

    return nodes, control_nodes


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    server = Server()
    await server.init()
    server.set_endpoint(settings.opcua_server_endpoint)
    server.set_server_name("Industrial Predictive Maintenance Motor Simulator")

    namespace_index = await server.register_namespace(settings.namespace_uri)
    nodes, controls = await build_address_space(server, namespace_index)
    model = MotorModel()

    logger.warning(
        "Lab OPC UA endpoint uses SecurityPolicy=None. Do not expose it directly to an untrusted network."
    )
    logger.info("OPC UA endpoint: %s", settings.opcua_server_endpoint)
    logger.info("Namespace URI: %s (index=%s)", settings.namespace_uri, namespace_index)

    async with server:
        while True:
            fault_mode = str(await controls["fault_mode"].read_value()).upper()
            fault_intensity = float(await controls["fault_intensity"].read_value())
            target_load = float(await controls["target_load"].read_value())
            running_command = bool(await controls["running_command"].read_value())
            reset_fault = bool(await controls["reset_fault"].read_value())

            snapshot = model.step(
                settings.simulation_tick_seconds,
                fault_mode=fault_mode,
                fault_intensity=fault_intensity,
                target_load=target_load,
                running_command=running_command,
                reset_fault=reset_fault,
            )

            if reset_fault:
                await controls["fault_mode"].write_value(ua.Variant("NONE", ua.VariantType.String))
                await controls["fault_intensity"].write_value(ua.Variant(0.0, ua.VariantType.Double))
                await controls["reset_fault"].write_value(ua.Variant(False, ua.VariantType.Boolean))

            await nodes["voltage"].write_value(ua.Variant(snapshot.voltage, ua.VariantType.Double))
            await nodes["current"].write_value(ua.Variant(snapshot.current, ua.VariantType.Double))
            await nodes["power"].write_value(ua.Variant(snapshot.power, ua.VariantType.Double))
            await nodes["rpm"].write_value(ua.Variant(snapshot.rpm, ua.VariantType.Double))
            await nodes["load"].write_value(ua.Variant(snapshot.load, ua.VariantType.Double))
            await nodes["vibration"].write_value(ua.Variant(snapshot.vibration, ua.VariantType.Double))
            await nodes["motor_temperature"].write_value(ua.Variant(snapshot.motor_temperature, ua.VariantType.Double))
            await nodes["bearing_temperature"].write_value(ua.Variant(snapshot.bearing_temperature, ua.VariantType.Double))
            await nodes["ambient_temperature"].write_value(ua.Variant(snapshot.ambient_temperature, ua.VariantType.Double))
            await nodes["running"].write_value(ua.Variant(snapshot.running, ua.VariantType.Boolean))
            await nodes["operating_hours"].write_value(ua.Variant(snapshot.operating_hours, ua.VariantType.Double))
            await nodes["fault_mode"].write_value(ua.Variant(snapshot.fault_mode, ua.VariantType.String))
            await nodes["fault_progress"].write_value(ua.Variant(snapshot.fault_progress, ua.VariantType.Double))

            await asyncio.sleep(settings.simulation_tick_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
