package com.neom.oxagon.sap;

import java.security.MessageDigest;
import java.time.Instant;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Receives near-real-time SAP S/4 outbound notifications for shipment
 * lifecycle events (ShipmentCreated, ShipmentChanged, ShipmentCanceled).
 *
 * SAP signs notifications with an HMAC-SHA256 digest over the raw body
 * using a pre-shared key. We verify before publishing to Kafka.
 */
@RestController
@RequestMapping("/api/v1/webhooks/sap")
public class WebhookHandler {

    private static final Logger log = LoggerFactory.getLogger(WebhookHandler.class);
    private static final String TOPIC = "oxagon.shipments.events.v1";

    private final KafkaTemplate<String, String> kafka;

    @Value("${oxagon.sap.webhook.shared-secret}")
    private String sharedSecret;

    public WebhookHandler(KafkaTemplate<String, String> kafka) {
        this.kafka = kafka;
    }

    @PostMapping("/shipment")
    public ResponseEntity<Void> onShipment(@RequestHeader("X-SAP-Signature") String signature,
                                           @RequestHeader("X-SAP-Event") String eventType,
                                           @RequestBody String body) {
        if (!verify(signature, body)) {
            log.warn("Rejecting SAP webhook: bad signature, event={}", eventType);
            return ResponseEntity.status(401).build();
        }
        var key = ShipmentRecordMapper.extractShipmentId(body);
        var envelope = """
            {"eventType":"%s","receivedAt":"%s","payload":%s}
            """.formatted(eventType, Instant.now(), body).trim();
        kafka.send(TOPIC, key, envelope);
        log.info("Forwarded SAP webhook event={} shipment={}", eventType, key);
        return ResponseEntity.accepted().build();
    }

    private boolean verify(String providedHex, String body) {
        try {
            var mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(sharedSecret.getBytes(), "HmacSHA256"));
            var expected = mac.doFinal(body.getBytes());
            var provided = hexToBytes(providedHex);
            return MessageDigest.isEqual(expected, provided);
        } catch (Exception e) {
            log.error("HMAC verification failed", e);
            return false;
        }
    }

    private static byte[] hexToBytes(String hex) {
        var out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }
}
