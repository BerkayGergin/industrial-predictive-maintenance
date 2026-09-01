# Analytics Design

## 1. Load-compensated anomaly detection

Raw temperature/current/vibration naturally change with load. Scoring raw values alone would create false anomalies during normal production cycles. The anomaly engine therefore builds residual features:

```text
vibration residual = measured vibration - expected vibration(load)
current residual   = measured current - expected current(load)
thermal residuals = measured temperature - expected temperature(load, ambient)
```

The first `ANOMALY_BASELINE_SAMPLES` (default 30) form a healthy baseline. Mean and standard deviation are calculated per residual feature, with minimum standard-deviation floors to avoid division by near-zero noise.

After warm-up the baseline is frozen. Each new residual becomes an absolute z-score. The strongest two z-scores produce a normalized anomaly score from 0 to 1.

The baseline is saved in the `analytics_state` table and restored after a collector restart.

## 2. Health score

Health starts at 100 and receives explainable penalties from:
- vibration
- bearing temperature
- motor temperature
- current relative to its expected operating point
- statistical anomaly score

State thresholds:
- `HEALTHY`: 80–100
- `WARNING`: 60–79
- `CRITICAL`: below 60

Hard critical sensor limits can force `CRITICAL` even before the combined score falls below 60.

The dashboard shows the strongest contributors and a deterministic maintenance recommendation. The recommendation is not generative AI; it is a transparent rule mapping.

## 3. Alarm rules

Open alarms are persistent state, not a transient browser notification.

Lifecycle:

```text
ACTIVE -> ACKNOWLEDGED -> CLEARED
```

If an acknowledged warning escalates to critical, the collector re-activates it so the new severity requires operator attention again.

Rules include high vibration, high bearing temperature, high motor temperature, anomaly detected and low health score.

## What this project does *not* claim

This is condition monitoring and anomaly-based predictive-maintenance prototyping. It does not calculate Remaining Useful Life (RUL), probability of failure, or a certified trip/protection decision. Those require real historical failure labels, asset-specific thresholds and validation.
