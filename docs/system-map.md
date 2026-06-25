# System Map — Integrations

## External systems

| System | Owner | Protocol | Auth | Direction |
|---|---|---|---|---|
| SAP S/4HANA (NEOM corporate) | NEOM IT — ERP | OData v4 + outbound webhook | OAuth2 client-credentials + HMAC-SHA256 | inbound (master), inbound (events) |
| Saudi Customs Fasah | ZATCA / Saudi Customs | REST / JSON | OAuth2 client-credentials | outbound (submissions), inbound (status webhook) |
| Navis N4 (oxagon-terminals) | Tenant: Oxagon Terminals | Kafka + REST | mTLS | inbound (gate / yard moves) |
| CommTrac TOS (sindalah-logistics) | Tenant: Sindalah Logistics | SFTP CSV drops | SSH key | inbound (gate events, 5-min) |
| Looker (NEOM BI) | NEOM Data Platform | DB + Git sync | IAM + service account | outbound (views, dashboards) |
| Tenant portal S3 (per-tenant) | NEOM Platform | S3 PUT | IRSA | outbound (PDF reports) |

## Topic ownership

| Kafka topic | Producer | Consumers |
|---|---|---|
| `oxagon.shipments.master.v1` | sap-integration | customs-fasah, dashboard, tenant-reports |
| `oxagon.shipments.events.v1` | sap-integration (webhook) | dashboard |
| `oxagon.yard.gate.events.v1` | tenant WMS adapters | dwell-time |
| `oxagon.yard.move.events.v1` | tenant WMS adapters | dwell-time |
| `oxagon.metrics.dwell.v1` | dwell-time | tenant-reports, alerting |
| `oxagon.customs.status.v1` | customs-fasah | dashboard, tenant-reports |

## SLAs (external)

- SAP: 99.5% availability, EOM cutover window the last Friday of each month.
- Fasah: 99.0%, scheduled maintenance Friday 02:00–04:00 AST.
- Navis N4 (oxagon-terminals): operates 24/7; Kafka producer maintained by tenant.
