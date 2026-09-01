from __future__ import annotations

SENSOR_NODE_IDS: dict[str, str] = {
    "voltage": "Motor_01.Electrical.Voltage",
    "current": "Motor_01.Electrical.Current",
    "power": "Motor_01.Electrical.Power",
    "rpm": "Motor_01.Mechanical.RPM",
    "load": "Motor_01.Mechanical.Load",
    "vibration": "Motor_01.Mechanical.Vibration",
    "motor_temperature": "Motor_01.Thermal.MotorTemperature",
    "bearing_temperature": "Motor_01.Thermal.BearingTemperature",
    "ambient_temperature": "Motor_01.Thermal.AmbientTemperature",
    "running": "Motor_01.Status.Running",
    "operating_hours": "Motor_01.Status.OperatingHours",
    "fault_mode": "Motor_01.Status.FaultMode",
    "fault_progress": "Motor_01.Status.FaultProgress",
}

CONTROL_NODE_IDS: dict[str, str] = {
    "fault_mode": "Motor_01.Controls.FaultMode",
    "fault_intensity": "Motor_01.Controls.FaultIntensity",
    "target_load": "Motor_01.Controls.TargetLoad",
    "running_command": "Motor_01.Controls.RunningCommand",
    "reset_fault": "Motor_01.Controls.ResetFault",
}

ALL_NODE_IDS = {**SENSOR_NODE_IDS, **{f"control_{k}": v for k, v in CONTROL_NODE_IDS.items()}}

FAULT_MODES = ("NONE", "BEARING_WEAR", "MISALIGNMENT", "OVERLOAD", "COOLING_FAILURE")
