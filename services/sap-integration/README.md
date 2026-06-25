# sap-integration

Spring Boot service that syncs shipment master data from SAP S/4HANA into the Oxagon platform via OData v4.

Tracks [KAN-35](https://neom.atlassian.net/browse/KAN-35) (DONE — cutover complete) and follow-up [KAN-54](https://neom.atlassian.net/browse/KAN-54).

## Responsibilities

- Periodic delta-sync of `A_Shipment`, `A_ShipmentItem`, `A_BusinessPartner` entities from SAP via OData v4.
- Webhook handler for real-time `ShipmentCreated` / `ShipmentUpdated` notifications.
- Publishes normalized `shipment.master.v1` events onto the `oxagon.shipments` Kafka topic.

## OData endpoints (SAP)

| Entity Set | Purpose |
|---|---|
| `/sap/opu/odata4/sap/api_shipment_srv/srvd_a2x/sap/shipment/0001/Shipment` | shipment headers |
| `/sap/opu/odata4/sap/api_shipment_srv/srvd_a2x/sap/shipment/0001/ShipmentItem` | line items |
| `/sap/opu/odata4/sap/api_business_partner/srvd_a2x/sap/businesspartner/0001/A_BusinessPartner` | tenants / shippers |

## Configuration

```yaml
oxagon:
  sap:
    base-url: https://sap-s4-staging.neom.internal
    auth:
      type: oauth2-client-credentials
      token-url: https://sap-s4-staging.neom.internal/sap/bc/sec/oauth2/token
    delta:
      poll-interval: PT5M
      page-size: 500
```

## Run locally

```bash
./mvnw spring-boot:run
```

## Known issues

- [KAN-54](https://neom.atlassian.net/browse/KAN-54) — delta sync skips shipments with > 64-char descriptions.
