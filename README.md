# Oxagon — Industrial Port & Logistics Visibility

End-to-end shipment, yard, and customs visibility platform for the Oxagon industrial port at NEOM. Provides a single pane of glass across tenant operators, SAP S/4HANA, Saudi Customs (Fasah), and on-prem yard systems.

Tracks Jira epic [KAN-21](https://neom.atlassian.net/browse/KAN-21).

## Tenants

The port is a multi-tenant facility. Each tenant (terminal operator, heavy-industry shipper, 3PL) gets:
- An isolated logical namespace for shipments, gate events, and dwell metrics.
- Row-level security in PostgreSQL keyed on `tenant_id`.
- Their own Looker workspace and SLA report.

Tenants currently onboarded (staging): `oxagon-terminals`, `neom-green-hydrogen`, `tonomus`, `sindalah-logistics`.

## System Map

```
                       +----------------------+
                       |   Tenant WMS / TOS   |
                       +----------+-----------+
                                  |
                          gate-in / gate-out
                          events  (Kafka)
                                  v
+-------------------+   +-----------------------+   +------------------+
|   SAP S/4HANA     |-->|   Oxagon Platform     |<--|  Saudi Customs   |
|  (shipment mgmt)  |   |  - shipment service   |   |     (Fasah)      |
|  OData v4         |   |  - dwell-time engine  |   |  pre-clearance   |
+-------------------+   |  - tenant reports     |   +------------------+
                        |  - dashboard (Next.js)|
                        +-----------+-----------+
                                    |
                                    v
                              PostgreSQL +
                              Looker (BI)
```

See [docs/system-map.md](docs/system-map.md) for full integration map.

## Getting Started

```bash
# Spin up local stack (Kafka, Postgres, mocks)
docker compose up -d

# Java service (SAP integration)
cd services/sap-integration && ./mvnw spring-boot:run

# Python services
cd services/customs-fasah && pip install -r requirements.txt && python -m src.preclearance
cd services/dwell-time && pip install -r requirements.txt && python -m src.gate_consumer
cd services/tenant-reports && pip install -r requirements.txt && python -m src.generator

# Dashboard
cd apps/dashboard && pnpm install && pnpm dev
```

## Services

| Service | Stack | Purpose | Jira |
|---|---|---|---|
| [sap-integration](services/sap-integration/) | Java 21 / Spring Boot | OData v4 delta sync of shipment master from SAP S/4 | [KAN-35](https://neom.atlassian.net/browse/KAN-35) |
| [customs-fasah](services/customs-fasah/) | Python 3.11 | Pre-clearance submissions to Saudi Customs Fasah API | [KAN-36](https://neom.atlassian.net/browse/KAN-36), [KAN-53](https://neom.atlassian.net/browse/KAN-53) |
| [dwell-time](services/dwell-time/) | Python + Kafka | Gate-in / gate-out event consumer; dwell metrics | [KAN-34](https://neom.atlassian.net/browse/KAN-34) |
| [tenant-reports](services/tenant-reports/) | Python + Looker | Monthly tenant SLA report generation | [KAN-37](https://neom.atlassian.net/browse/KAN-37) |
| [apps/dashboard](apps/dashboard/) | Next.js / React | Operator dashboard | — |

## Jira

- Epic: [KAN-21 — Oxagon Industrial Port & Logistics Visibility](https://neom.atlassian.net/browse/KAN-21)
- Active sprint board: [Sprint 24](https://neom.atlassian.net/jira/software/projects/KAN/boards/1)

## Owners

See [.github/CODEOWNERS](.github/CODEOWNERS). Primary: `@neom-oxagon-leads`, data path: `@neom-platform-data`.
