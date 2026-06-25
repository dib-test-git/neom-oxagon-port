# Architecture

## Overview

The Oxagon platform stitches together SAP S/4HANA (the source of truth for shipment master), tenant Warehouse / Terminal Operating Systems (Navis N4 and CommTrac, primarily), and Saudi Customs (Fasah) into a single tenant-aware view of port operations.

## Components

- **sap-integration** (Java / Spring Boot): polls SAP OData v4 for shipment-master deltas and accepts SAP outbound webhooks. Publishes onto `oxagon.shipments.master.v1`.
- **customs-fasah** (Python): consumes shipment-master events, builds Fasah PreClearanceManifest payloads, submits, and tracks status.
- **dwell-time** (Python / Kafka): consumes gate and yard-move events, computes per-container dwell windows.
- **tenant-reports** (Python): generates monthly SLA PDF + Looker dashboards per tenant.
- **apps/dashboard** (Next.js): operator UI.

## Data flow

1. SAP → `sap-integration` → Kafka `oxagon.shipments.master.v1`.
2. `customs-fasah` consumes, submits to Fasah, writes `customs_status` row.
3. Tenant WMS → Kafka `oxagon.yard.gate.events.v1` → `dwell-time` → `dwell_windows` table.
4. Looker reads `dwell_metrics` view; operator dashboard reads via the Next.js API.

## Tenancy

All Postgres tables carry a `tenant_id` column with row-level security policies. Kafka topics are shared but consumers filter on `tenant_id` in the message envelope.

## Non-goals (for v1)

- Real-time crane optimisation (handled by Navis N4 natively).
- Vessel berth-window planning (out of scope, handled by Port Authority's TIDEWORKS).
