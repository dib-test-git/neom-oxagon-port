"""Gate-event consumer.

Consumes `oxagon.yard.gate.events.v1`, opens a dwell-window in Postgres
on GATE_IN, closes it on GATE_OUT, and emits a `oxagon.metrics.dwell.v1`
event when the window closes.

Tracks KAN-34.
"""
from __future__ import annotations

import json
import os
import signal
import sys
from datetime import datetime
from typing import Literal

import psycopg
import structlog
from confluent_kafka import Consumer, Producer
from prometheus_client import Counter, Histogram, start_http_server
from pydantic import BaseModel, Field, ValidationError

from .dwell_metrics import close_window, now_utc, open_window

log = structlog.get_logger(__name__)

GATE_TOPIC = "oxagon.yard.gate.events.v1"
DWELL_TOPIC = "oxagon.metrics.dwell.v1"
CONSUMER_GROUP = "dwell-time-gate"

# Late-event tolerance: events older than 24h are routed to the DLQ rather
# than reopening a closed window.
LATE_EVENT_TOLERANCE_SEC = 24 * 3600

events_total = Counter(
    "oxagon_gate_events_total", "Gate events consumed", ["tenant", "event_type"]
)
dwell_seconds = Histogram(
    "oxagon_dwell_seconds", "Closed dwell windows (seconds)", ["tenant"],
    buckets=(3600, 6 * 3600, 12 * 3600, 24 * 3600, 48 * 3600, 72 * 3600, 7 * 24 * 3600),
)


class GateEvent(BaseModel):
    tenant_id: str
    container_number: str
    event_type: Literal["GATE_IN", "GATE_OUT"]
    truck_plate: str | None = None
    lane: str
    occurred_at: datetime
    yard_block: str | None = None
    source_system: str = Field(default="navis-n4")


def is_too_late(event: GateEvent) -> bool:
    return (now_utc() - event.occurred_at).total_seconds() > LATE_EVENT_TOLERANCE_SEC


def handle_event(conn: psycopg.Connection, producer: Producer, event: GateEvent) -> None:
    if is_too_late(event):
        log.warning(
            "gate.event.too_late",
            tenant=event.tenant_id,
            container=event.container_number,
            occurred_at=event.occurred_at.isoformat(),
        )
        # In production this would route to a DLQ topic. Skip for now.
        return

    if event.event_type == "GATE_IN":
        open_window(conn, event.tenant_id, event.container_number, event.occurred_at, event.yard_block)
    else:
        window = close_window(conn, event.tenant_id, event.container_number, event.occurred_at)
        if window is None:
            return
        secs = window.dwell_seconds or 0
        dwell_seconds.labels(event.tenant_id).observe(secs)
        producer.produce(
            DWELL_TOPIC,
            key=f"{event.tenant_id}:{event.container_number}",
            value=json.dumps({
                "tenant_id": event.tenant_id,
                "container_number": event.container_number,
                "gate_in_at": window.gate_in_at.isoformat(),
                "gate_out_at": window.gate_out_at.isoformat() if window.gate_out_at else None,
                "dwell_seconds": secs,
                "yard_block": window.yard_block,
            }).encode(),
        )
    events_total.labels(event.tenant_id, event.event_type).inc()


def main() -> None:
    start_http_server(int(os.environ.get("METRICS_PORT", "9100")))

    consumer = Consumer({
        "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092"),
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "max.poll.interval.ms": 600000,
    })
    consumer.subscribe([GATE_TOPIC])

    producer = Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092")})
    conn = psycopg.connect(os.environ["POSTGRES_URL"])

    shutdown = False

    def stop(_signum, _frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        while not shutdown:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                producer.poll(0)
                continue
            if msg.error():
                log.error("kafka.error", error=str(msg.error()))
                continue
            try:
                event = GateEvent.model_validate_json(msg.value())
            except ValidationError as e:
                log.error("gate.event.invalid", error=str(e), raw=msg.value()[:200])
                consumer.commit(message=msg)
                continue
            try:
                handle_event(conn, producer, event)
                consumer.commit(message=msg)
            except Exception:
                log.exception("gate.event.handle_failed", tenant=event.tenant_id)
                conn.rollback()
    finally:
        consumer.close()
        producer.flush(10)
        conn.close()
        log.info("gate_consumer.stopped")


if __name__ == "__main__":
    sys.exit(main())
