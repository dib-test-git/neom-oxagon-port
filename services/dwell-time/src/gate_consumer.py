"""Gate-event consumer.

Skeleton. The full implementation — including yard-move correlation,
late-event handling, and out-of-order tolerance — is being delivered
in feat/gate-in-pipeline (KAN-34).
"""
from __future__ import annotations

import json
import os
from typing import Literal

import structlog
from confluent_kafka import Consumer
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)

GATE_TOPIC = "oxagon.yard.gate.events.v1"
CONSUMER_GROUP = "dwell-time-gate"


class GateEvent(BaseModel):
    tenant_id: str
    container_number: str
    event_type: Literal["GATE_IN", "GATE_OUT"]
    truck_plate: str | None = None
    lane: str
    occurred_at: str  # ISO-8601
    yard_block: str | None = None
    source_system: str = Field(default="navis-n4")


def main() -> None:
    consumer = Consumer({
        "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([GATE_TOPIC])
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                log.error("kafka.error", error=str(msg.error()))
                continue
            event = GateEvent.model_validate_json(msg.value())
            # TODO(KAN-34): open/close dwell-window in Postgres and emit metric.
            log.info(
                "gate.event",
                tenant=event.tenant_id,
                container=event.container_number,
                type=event.event_type,
            )
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
