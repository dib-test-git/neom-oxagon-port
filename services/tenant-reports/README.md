# tenant-reports

Monthly **tenant SLA report** generator. Pulls dwell, gate, and customs metrics from Postgres and Looker, renders a per-tenant PDF, and uploads it to the tenant portal bucket.

Tracks [KAN-37](https://neom.atlassian.net/browse/KAN-37).

## SLA metrics

| Metric | Target | Source |
|---|---|---|
| Container avg dwell time | < 72h (import) / < 48h (export) | `dwell_metrics` |
| Gate-truck turn time p95 | < 35 min | `gate_events` |
| Customs pre-clearance lead time p95 | < 2h | `customs_status` |
| Yard-move accuracy | > 99.5% | tenant WMS reconciliation |

## Run

```bash
pip install -r requirements.txt
python -m src.generator --tenant oxagon-terminals --month 2026-05
```

## Looker

Views are checked in under [looker_views/](looker_views/) and synced to the BI project via the Looker Git integration.
