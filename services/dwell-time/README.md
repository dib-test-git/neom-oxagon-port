# dwell-time

Kafka consumer that tracks container **dwell time** from gate-in to gate-out, and yard-block residence time.

Tracks [KAN-34](https://neom.atlassian.net/browse/KAN-34).

## Inputs

| Topic | Source | Schema |
|---|---|---|
| `oxagon.yard.gate.events.v1` | Tenant WMS / TOS (Navis N4, CommTrac) | `GateEvent` (see `src/gate_consumer.py`) |
| `oxagon.yard.move.events.v1` | RTG/RMG telemetry | `YardMove` |

## Outputs

- `dwell_metrics` Postgres table — per-container dwell windows, computed lazily on gate-out.
- `oxagon.metrics.dwell.v1` Kafka topic — emits dwell-window-closed events for Looker / alerting.

## Run

```bash
pip install -r requirements.txt
python -m src.gate_consumer
```
