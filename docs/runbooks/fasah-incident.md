# Runbook — Fasah pre-clearance incidents

**Service**: `customs-fasah`  •  **Severity baseline**: P2 (P1 if any tenant has > 4h customs queue)
**On-call**: `#oncall-oxagon-platform`  •  **Jira**: [KAN-36](https://neom.atlassian.net/browse/KAN-36), [KAN-53](https://neom.atlassian.net/browse/KAN-53)

## Symptoms

- Looker board "Customs — submission backlog" shows backlog > 200 manifests for any tenant.
- Datadog monitor `customs.fasah.submit.error_rate` over 5% for 10 minutes.
- Sentry `FasahError` spike.

## Triage (first 10 min)

1. Check Fasah status page: <https://status.fasah.sa>.
2. Inspect last 50 errors:
   ```bash
   kubectl logs -n oxagon -l app=customs-fasah --since=15m | grep fasah.error
   ```
3. Confirm whether errors are 5xx (transient — let retries run) or 4xx (manifest schema — needs code fix).

## Known issue: vessels > 8000 TEU time out (KAN-53)

If errors show `httpx.ReadTimeout` and shipment payload has > ~2500 containers, this is the known timeout.

Mitigation while fix is rolling out:

1. Set `FASAH_MAX_CONTAINERS_PER_SUBMISSION=1500` in the deployment (`kubectl set env deploy/customs-fasah FASAH_MAX_CONTAINERS_PER_SUBMISSION=1500`).
2. Roll the deployment.
3. Re-queue failed shipments via `python -m src.requeue --since 1h`.

## Escalation

- > 30 min unmitigated: page `@neom-oxagon-leads`.
- Tenant-visible: notify tenant via `#tenant-<id>-ops` Slack channel.
- Regulator-visible (Fasah rejects > 100 manifests): comms to Customs liaison `customs-liaison@neom.com`.

## Post-incident

- File or update Jira incident under KAN epic.
- Add a regression test under `services/customs-fasah/tests/test_fasah_client.py`.
