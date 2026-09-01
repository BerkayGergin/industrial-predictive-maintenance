# OPC UA Information Model

Namespace URI: `urn:factory:predictive-maintenance`

The client discovers the runtime namespace index by URI; it never hardcodes `ns=2`.

```text
Objects
└── Factory
    └── Motor_01
        ├── Electrical
        │   ├── Voltage
        │   ├── Current
        │   └── Power
        ├── Mechanical
        │   ├── RPM
        │   ├── Load
        │   └── Vibration
        ├── Thermal
        │   ├── MotorTemperature
        │   ├── BearingTemperature
        │   └── AmbientTemperature
        ├── Status
        │   ├── Running
        │   ├── OperatingHours
        │   ├── FaultMode
        │   └── FaultProgress
        └── Controls
            ├── FaultMode          (writable)
            ├── FaultIntensity     (writable)
            ├── TargetLoad         (writable)
            ├── RunningCommand     (writable)
            └── ResetFault         (writable)
```

## Stable string NodeIds

Examples:

- `Motor_01.Mechanical.RPM`
- `Motor_01.Mechanical.Vibration`
- `Motor_01.Thermal.BearingTemperature`
- `Motor_01.Controls.FaultMode`

At runtime they appear as e.g. `ns=2;s=Motor_01.Mechanical.RPM`, but the namespace index can differ if the server's namespace table changes.

## Subscription settings

Defaults:
- sampling interval: 250 ms
- publishing interval: 500 ms
- historian snapshot interval: 1 s

The subscription callback updates the newest value cache. The collector then writes a coherent 1-second snapshot instead of one database row for every individual node notification.

## Lab security

The OPC UA endpoint deliberately uses `SecurityPolicy=None` because all services run on the local Docker network and the project is for learning. Do not expose this endpoint to an untrusted network. Production OPC UA normally uses certificates, secure policies and application/user identity controls.
