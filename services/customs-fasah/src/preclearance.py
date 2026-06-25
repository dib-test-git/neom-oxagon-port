"""Pre-clearance orchestrator.

Consumes shipment-master events from Kafka, builds Fasah PreClearanceManifest
payloads, and submits them.

Tracks KAN-36.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

import structlog
from confluent_kafka import Consumer

from .chunker import ManifestChunker
from .fasah_client import FasahClient, FasahCredentials

log = structlog.get_logger(__name__)

SHIPMENT_TOPIC = "oxagon.shipments.master.v1"
CONSUMER_GROUP = "customs-fasah-preclearance"


@dataclass
class PreClearanceConfig:
    max_containers_per_submission: int = int(
        os.environ.get("FASAH_MAX_CONTAINERS_PER_SUBMISSION", "2500")
    )


def build_manifest(shipment: dict[str, Any], tenant: dict[str, Any]) -> dict[str, Any]:
    """Map an internal shipment record to a Fasah PreClearanceManifest payload."""
    return {
        "vesselImo": shipment["vesselImo"],
        "voyageNumber": shipment["voyageNumber"],
        "portOfDischarge": "SAOXG",  # Oxagon port code
        "importer": {
            "crNumber": tenant["commercialRegistrationNumber"],
            "vatNumber": tenant.get("vatNumber"),
            "tenantId": tenant["id"],
        },
        "containers": [
            {
                "containerNumber": c["containerNumber"],
                "sealNumber": c.get("sealNumber"),
                "isoType": c["isoType"],
                "grossWeightKg": c["grossWeightKg"],
                "hsCodes": c.get("hsCodes", []),
                "commodityDescription": c["commodityDescription"],
            }
            for c in shipment["containers"]
        ],
    }


async def process(client: FasahClient, chunker: ManifestChunker, shipment: dict[str, Any], tenant: dict[str, Any]) -> list[str]:
    """Submit a shipment's manifest, chunking if needed (KAN-53 workaround)."""
    manifest = build_manifest(shipment, tenant)
    refs: list[str] = []
    for chunk in chunker.chunk(manifest):
        result = await client.submit_preclearance(chunk)
        refs.append(result["fasahReferenceNumber"])
    return refs


async def main() -> None:
    creds = FasahCredentials.from_env()
    client = FasahClient(creds)
    cfg = PreClearanceConfig()
    chunker = ManifestChunker(max_containers=cfg.max_containers_per_submission)

    consumer = Consumer({
        "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([SHIPMENT_TOPIC])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0)
                continue
            if msg.error():
                log.error("kafka.error", error=str(msg.error()))
                continue
            payload = json.loads(msg.value())
            try:
                refs = await process(client, chunker, payload["shipment"], payload["tenant"])
                log.info("preclearance.ok", shipment=payload["shipment"]["id"], refs=refs)
                consumer.commit(message=msg)
            except Exception as e:
                log.exception("preclearance.fail", shipment=payload.get("shipment", {}).get("id"), error=str(e))
    finally:
        consumer.close()
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
