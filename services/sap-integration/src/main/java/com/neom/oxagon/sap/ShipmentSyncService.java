package com.neom.oxagon.sap;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

/**
 * Periodically pulls shipment-master deltas from SAP S/4HANA and
 * republishes them onto the `oxagon.shipments` Kafka topic.
 *
 * Delta strategy: high-watermark on LastChangeDateTime, persisted in
 * the `sap_sync_state` table.
 *
 * Tracks KAN-35.
 */
@Service
public class ShipmentSyncService {

    private static final Logger log = LoggerFactory.getLogger(ShipmentSyncService.class);
    private static final String SHIPMENT_ENTITY_SET = "/sap/opu/odata4/sap/api_shipment_srv/srvd_a2x/sap/shipment/0001/Shipment";
    private static final String KAFKA_TOPIC = "oxagon.shipments.master.v1";

    private final OData4Client odata;
    private final KafkaTemplate<String, String> kafka;
    private final SyncStateRepository stateRepo;

    @Value("${oxagon.sap.delta.page-size:500}")
    private int pageSize;

    public ShipmentSyncService(OData4Client odata,
                               KafkaTemplate<String, String> kafka,
                               SyncStateRepository stateRepo) {
        this.odata = odata;
        this.kafka = kafka;
        this.stateRepo = stateRepo;
    }

    @Scheduled(fixedDelayString = "${oxagon.sap.delta.poll-interval-ms:300000}")
    public void runDelta() {
        var highWatermark = stateRepo.lastSyncedAt("Shipment").orElse(Instant.EPOCH);
        log.info("SAP shipment delta sync starting; highWatermark={}", highWatermark);

        var totalSynced = 0;
        var nextUrl = Optional.<String>empty();
        var query = baseQuery(highWatermark);

        try {
            do {
                var resp = nextUrl.isPresent()
                    ? odata.get(nextUrl.get(), Map.of())
                    : odata.get(SHIPMENT_ENTITY_SET, query);

                if (resp.statusCode() != 200) {
                    log.error("SAP returned {} on shipment delta; aborting", resp.statusCode());
                    return;
                }

                totalSynced += publish(resp.body());
                nextUrl = odata.nextLink(resp.body());
            } while (nextUrl.isPresent());

            stateRepo.upsertLastSyncedAt("Shipment", Instant.now());
            log.info("SAP shipment delta sync complete; synced={} since={}", totalSynced, highWatermark);
        } catch (Exception e) {
            log.error("SAP shipment delta sync failed", e);
        }
    }

    private Map<String, String> baseQuery(Instant since) {
        var q = new LinkedHashMap<String, String>();
        q.put("$top", String.valueOf(pageSize));
        q.put("$orderby", "LastChangeDateTime asc");
        q.put("$filter", "LastChangeDateTime gt " + DateTimeFormatter.ISO_INSTANT.format(since));
        q.put("$select", "Shipment,ShipmentType,ShippingType,TransportationMode,"
            + "LoadingPoint,UnloadingPoint,ShippingProcessing,"
            + "ShipmentDescription,LastChangeDateTime,CreationDateTime");
        return q;
    }

    private int publish(String json) {
        // Real implementation: Jackson stream-parse "value": [...] and emit each record.
        // For clarity here we delegate to a record mapper.
        var records = ShipmentRecordMapper.parse(json);
        records.forEach(r -> kafka.send(KAFKA_TOPIC, r.shipmentId(), r.toJson()));
        return records.size();
    }
}
