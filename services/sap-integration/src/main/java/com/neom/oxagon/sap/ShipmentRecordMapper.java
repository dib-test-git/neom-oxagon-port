package com.neom.oxagon.sap;

import java.util.List;

/**
 * Maps SAP OData JSON payloads to internal ShipmentRecord events.
 * Real implementation uses Jackson stream-parsing; stubbed here.
 */
public final class ShipmentRecordMapper {

    private ShipmentRecordMapper() {}

    public record ShipmentRecord(String shipmentId, String tenantId, String json) {
        public String toJson() { return json; }
    }

    public static List<ShipmentRecord> parse(String odataBody) {
        // TODO: implement Jackson stream parsing of `value` array.
        return List.of();
    }

    public static String extractShipmentId(String body) {
        var marker = "\"Shipment\":\"";
        var i = body.indexOf(marker);
        if (i < 0) return "unknown";
        i += marker.length();
        var j = body.indexOf('"', i);
        return body.substring(i, j);
    }
}
